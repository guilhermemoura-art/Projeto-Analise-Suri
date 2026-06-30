import re
import pandas as pd

# Padrões extraídos dos 39 templates oficiais do chatbot Suri/Tactu
# Aplicados apenas em AgentMessage — UserMessage nunca é filtrada aqui
AUTOMATED_PATTERNS = [

    # ── GE01 / GE1: Boas-vindas (PT/EN/ES) ──────────────────────────────
    r"Sou a Tatiana, sua assistente virtual de hospedagem",
    r"Sou a Tatiana, sua assistente virtual da",
    r"I'm Tatiana, your virtual hosting assistant",
    r"Guia de Estadias",
    r"Accommodation Guide",
    r"Guía de Estancias",

    # ── Marcadores genéricos de automação (PT/EN/ES) ──────────────────────
    r"Esta mensagem é automática e não necessita de resposta",
    r"This message is automatic and does not require a chat response",
    r"Este mensaje es automático y no requiere respuesta por chat",
    r"This is an automatic message and does not require a chat response",

    # ── GE02: Instruções iniciais — formulário obrigatório ────────────────
    r"formulário.{0,25}obrigatório e sem ele",
    r"form is mandatory and without it",
    r"formulario es obligatorio y sin él",
    r"Estamos animados para a sua chegada e preparando tudo",
    r"We are excited for your arrival and are preparing everything",
    r"Estamos entusiasmados con tu llegada y estamos preparando",
    r"taxa de energia de R\$\d+[,.]\d+ por kWh",
    r"medidor elétrico é conferido antes e depois da estadia",

    # ── GE03: Orientações de check-in ────────────────────────────────────
    r"Lembre-se que você NÃO poderá entrar no imóvel",
    r"Remember that you will NOT be able to enter the property",
    r"Recuerda que NO podrás entrar a la propiedad",
    r"favorite essa mensagem para que possa encontrá-la mais facilmente no dia do check-in",
    r"bookmark this message so you can easily find it on the day of check-in",
    r"guarda este mensaje en tus favoritos",

    # ── GE03.1: Lembrete de formulário pendente ───────────────────────────
    r"ainda não respondeu o formulário de check.?in",
    r"haven.t filled out the check.in form yet",
    r"aún no has respondido al formulario de check.in",
    r"SUA ENTRADA NA ACOMODAÇÃO NÃO SERÁ AUTORIZADA SEM PREENCHIMENTO DO FORMULÁRIO",
    r"YOU WILL NOT BE AUTHORIZED TO ENTER THE ACCOMMODATION WITHOUT COMPLETING THE FORM",
    r"NO SE AUTORIZARÁ TU ENTRADA AL ALOJAMIENTO SIN RELLENAR EL FORMULARIO",
    r"não deixe para a última hora.{0,60}estaremos recebendo outros hóspedes",
    r"Don.t leave it until the last minute.{0,60}receiving other guests",

    # ── GE04: Pré check-out ───────────────────────────────────────────────
    r"check.?out previsto para amanhã",
    r"check.?out scheduled for tomorrow",
    r"check.?out programado mañana",
    r"Retire o lixo e lave a louça",
    r"Take out the trash and wash the dishes",
    r"Sacar la basura y lavar los platos",
    r"Tranque o imóvel e nos avise ao sair",
    r"Lock the property and let us know when you.ve left",

    # ── GE05: Mensagem de check-out ──────────────────────────────────────
    r"breve verifica[çc][ãa]o do imóvel após sua saída",
    r"brief inspection of the property after your departure",
    r"breve revisión de la propiedad después de su salida",
    r"Agradeceríamos imensamente se você pudesse nos avaliar",
    r"We would greatly appreciate it if you could rate us",
    r"Te agradeceríamos mucho si pudieras calificarnos",

    # ── GE06/07/08: Pedidos de avaliação (PT/EN/ES) ───────────────────────
    r"2 minutos.{0,40}para nos avaliar",
    r"2 minutes.{0,40}to rate us",
    r"2 minutos.{0,40}para calificarnos",
    r"3 minutos para fazer uma avaliação 5 estrelas",
    r"3 minutes to leave a 5.star review",
    r"3 minutos para dejar una reseña de 5 estrellas",
    r"meta de avalia[çc][õo]es para bater",
    r"evaluation target to reach",
    r"objetivo de evaluación que alcanzar",
    r"últimos dias para você contribuir com uma avaliação 5 estrelas",
    r"last few days for you to contribute a 5.star review",
    r"últimos días para que aportes una reseña de 5 estrellas",
    r"Reparamos que você ainda não avaliou sua reserva",
    r"We noticed that you haven.t evaluated your reservation yet",
    r"Hemos notado que aún no has evaluado tu reserva",

    # ── GE09: Verificação final pós-estadia ───────────────────────────────
    r"Acabamos de finalizar o período de verificação",
    r"Gasto de Energia.{0,30}consumo foi de",
    r"Itens quebrado",
    r"nossa chave PIX",

    # ── GE10: Reserva cancelada (PT/EN/ES) ───────────────────────────────
    r"precisou cancelar sua reserva com a gente",
    r"had to cancel your reservation with us",
    r"tuviste que cancelar tu reserva con nosotros",
    r"reservas feitas diretamente no site da Tactu podem ser até 20% mais baratas",
    r"bookings made directly on the Tactu website can be up to 20% cheaper",
    r"Prefiro não responder",
    r"Prefiero no responder",
    r"I prefer not to respond",

    # ── GE11: Itens danificados ───────────────────────────────────────────
    r"Após sua partida, notamos um incidente que precisamos abordar",

    # ── GE12: Instruções Beach Park ───────────────────────────────────────
    r"Liberação na recepção via e-mail",
    r"Toalhas de Piscina.{0,30}Cartão na recepção",

    # ── Coleta de avaliações atrasadas ────────────────────────────────────
    r"você se hospedou em uma de nossas acomodações, mas ainda não tivemos o prazer de receber seu feedback",

    # ── Encerramento por inatividade ─────────────────────────────────────
    r"encerrando seu atendimento por inatividade",
    r"faz um tempinho desde nossa última interação",
    r"vamos encerrar este atendimento por agora",

    # ── CSAT — avaliação de qualidade do atendimento ──────────────────────
    r"Antes de nos despedirmos.{0,50}avaliar a qualidade do nosso atendimento",
    r"Me conta de 1 [aà] 5 o quanto você ficou satisfeito",

    # ── Pedido de avaliação no Airbnb ─────────────────────────────────────
    r"dedicar 2 minutos.{0,30}para nos avaliar no Airbnb",
    r"Sua avaliação é de extrema importância para nos ajudar a atingir nossas metas",
    r"instagram\.com/tactu\.homes",

    # ── Campanha late check-out ───────────────────────────────────────────
    r"#CompartilhandoMomentosTactu",
    r"@tactu\.homes",
    r"late check.?out por nossa conta",

    # ── Iniciar conversa ──────────────────────────────────────────────────
    r"equipe de atendimento Tactu",
    r"do atendimento da Tactu\.",

    # ── Menu IVR — seleção de assunto por número ──────────────────────────
    r"indique o número correspondente ao assunto que deseja tratar",

    # ── Fora do horário de atendimento ────────────────────────────────────
    r"equipe de atendimento.{0,10}não está disponível",
    r"nosso atendimento é de domingo a sábado",

    # ── Limitações do bot ─────────────────────────────────────────────────
    r"não consigo entender esse tipo de arquivo",

    # ── URLs de formulários / links enviados pelo agente ──────────────────
    r"checkin\.tactu\.com\.br",
    r"https?://\S+formulari[oa]",
    r"https?://\S+check.?in",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in AUTOMATED_PATTERNS]


def _is_automated_agent_message(text: str) -> bool:
    if not text or len(text.strip()) < 10:
        return True
    return any(p.search(text) for p in _COMPILED)


def filter_automated(messages_df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove SystemMessages e AgentMessages que correspondem aos templates
    oficiais do chatbot Tactu/Suri. Preserva todas as UserMessages
    e AgentMessages genuínas (respostas humanas do agente).
    """
    if messages_df.empty:
        return messages_df

    before = len(messages_df)

    mask_system = messages_df["type"] == "SystemMessage"

    mask_agent_automated = (messages_df["type"] == "AgentMessage") & messages_df[
        "text"
    ].apply(lambda t: _is_automated_agent_message(str(t) if pd.notna(t) else ""))

    result = messages_df[~(mask_system | mask_agent_automated)].copy()

    removed = before - len(result)
    print(
        f"Filtragem: {before} → {len(result)} mensagens "
        f"({removed} automáticas removidas — "
        f"{mask_system.sum()} SystemMessage + {mask_agent_automated.sum()} AgentMessage template)"
    )
    return result