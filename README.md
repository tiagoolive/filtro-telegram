# 🛒 Bot de Filtro de Promoções para Telegram

Este bot monitora automaticamente os canais e grupos de promoções em que sua conta do Telegram participa, filtra mensagens que contenham palavras-chave de seu interesse (ex: `rtx 4060`, `ps5`, `kindle`, `air fryer`), ignora termos indesejados (ex: `capa`, `película`, `recondicionado`) e encaminha as melhores ofertas diretamente para as suas **Mensagens Salvas** (ou para um canal privado de sua escolha).

---

## 🚀 Como Executar

### Opção 1: Pelo arquivo executável (Mais Fácil)

Basta dar **dois cliques no arquivo**:

```text
iniciar.bat
```

Ele cuidará de ativar o ambiente virtual, instalar os pacotes necessários e iniciar o bot.

### Opção 2: Pelo Terminal / PowerShell

```powershell
# Ativar o ambiente virtual
.\venv\Scripts\Activate.ps1

# Iniciar o bot
python main.py
```

---

## 🔑 Primeiro Acesso (Login no Telegram)

Na **primeira vez** que você iniciar o bot no terminal:

1. Ele solicitará o seu **número de telefone** com o código do país:
   - Exemplo: `+5511999999999`
2. O Telegram enviará um **código de confirmação** oficial dentro do seu aplicativo Telegram (ou SMS).
3. Digite o código no terminal e pressione Enter.
4. Se a sua conta possuir verificação em duas etapas (2FA), ele pedirá sua senha.
5. Pronto! Uma sessão segura (`filtro_promocoes.session`) será gerada no computador. Nas próximas inicializações, o login será **automático e instantâneo**.

---

## 📱 Controle Diretamente pelo Telegram!

Você não precisa abrir o código ou reiniciar o bot para mudar suas palavras-chave. Basta abrir a conversa de **Mensagens Salvas** no Telegram e enviar os comandos:

| Comando                | Descrição                                                            | Exemplo                                      |
| :--------------------- | :------------------------------------------------------------------- | :------------------------------------------- |
| `/ajuda`               | Mostra todos os comandos disponíveis                                 | `/ajuda`                                     |
| `/listar`              | Exibe todas as palavras ativas e bloqueadas                          | `/listar`                                    |
| `/add <termo>`         | Adiciona nova palavra-chave de busca (suporta teto de preço com `<`) | `/add rtx 4060 < 2000` ou `/add ps5, kindle` |
| `/del <termo>`         | Remove palavra-chave de busca                                        | `/del rtx 4060`                              |
| `/bloquear <termo>`    | Bloqueia ofertas que contenham esse termo                            | `/bloquear capa, case, pelicula`             |
| `/desbloquear <termo>` | Desbloqueia o termo                                                  | `/desbloquear capa`                          |
| `/canais`              | Lista os canais de promoções da sua conta                            | `/canais`                                    |
| `/modo`                | Alterna entre monitorar TODOS os canais ou apenas específicos        | `/modo`                                      |
| `/addcanal <@canal>`   | Adiciona um canal específico para monitorar                          | `/addcanal @promobitoficial`                 |
| `/status`              | Exibe estatísticas de tempo online e promoções capturadas            | `/status`                                    |
| `/limparhistorico`     | Limpa o histórico imediato de duplicatas                             | `/limparhistorico`                           |

---

## ⚙️ Arquivo de Configuração (`config.json`)

Você também pode configurar as palavras diretamente no arquivo `config.json`:

```json
{
  "monitor_all_channels": true,
  "channels": [],
  "keywords": [
    "rtx 4060",
    "rtx 4070",
    "ps5",
    "playstation 5",
    "nintendo switch",
    "kindle",
    "air fryer",
    "iphone"
  ],
  "negative_keywords": [
    "capa",
    "capinha",
    "pelicula",
    "suporte",
    "recondicionado",
    "usado"
  ],
  "target_chat": "me",
  "add_tag_reply": true,
  "cooldown_minutes": 15
}
```

### Explicação dos campos:

- **`monitor_all_channels`**: Quando `true`, monitora todos os canais e grupos em que você entrou. Se `false`, monitora apenas os canais listados em `channels`.
- **`keywords`**: Lista de palavras e frases que você quer buscar. Não diferencia maiúsculas de minúsculas e ignora acentos (ex: `promoção` acha `promocao`). Você também pode definir um **teto de preço** opcional usando `<` ou `<=` (ex: `"rtx 4060 < 2000"` só encaminhará se o valor encontrado na mensagem for menor ou igual a R$ 2.000).
- **`negative_keywords`**: Lista de palavras que fazem a mensagem ser **ignorada** mesmo se tiver a palavra-chave (ex: uma mensagem com "Capa para iPhone" será descartada se "capa" estiver na lista).
- **`target_chat`**: `"me"` para receber nas Mensagens Salvas, ou o `@nomedocanal` / ID de um canal criado por você.
- **`add_tag_reply`**: Quando `true`, o bot envia uma tag logo abaixo da mensagem encaminhada avisando qual palavra-chave ativou o alerta e o canal de origem.
- **`cooldown_minutes`**: Intervalo em minutos para evitar que a mesma promoção seja enviada repetidamente caso múltiplos canais postem o mesmo link.

---

## 🛡️ Segurança

- Seus dados de API (`api-id` e `api-hash`) já estão configurados no arquivo `.env`.
- **Nunca envie ou compartilhe** os arquivos `.env` e `.session` com terceiros, pois eles contêm o acesso à sua conta.
- O arquivo `.gitignore` já está configurado para proteger esses arquivos contra uploads acidentais no Git.
