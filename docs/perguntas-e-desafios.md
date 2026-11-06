# Sistema da Clínica: perguntas e desafios

Guia de estudo para a apresentação: perguntas que o professor pode fazer, com respostas, e pequenas alterações que ele pode pedir na hora.

## Visão geral

O sistema é um programa Python com telas em Tkinter e banco PostgreSQL, dividido em quatro partes, cada uma com uma tarefa só.

| Camada | Arquivos | O que faz |
| --- | --- | --- |
| Apresentação | apresentacao/janela.py | Telas Tkinter. Lê o que o usuário digitou e mostra resultados e erros. |
| Negócio | negocio/servicos.py, agenda.py, validacao.py | Valida os dados e aplica as regras. |
| Dados | dados/dao.py, conexao.py | Só SQL. Abre a conexão e executa as consultas. |
| Banco | sql/01_esquema.sql, 02_funcoes_gatilhos.sql, 03_dados_exemplo.sql | Tabelas, gatilhos e dados de exemplo no PostgreSQL. |

O caminho de um agendamento mostra as camadas trabalhando juntas:

1. O botão Agendar chama `AbaConsultas.ao_clicar_agendar`, em janela.py.
2. `AgendaService.agendar`, em agenda.py, valida os campos e junta data e hora.
3. `ConsultaDAO.inserir`, em dao.py, faz o INSERT na tabela consulta.
4. Os gatilhos do banco conferem conflito de agenda e horário do médico. Se recusarem, o erro volta como `ErroBanco` e a função `executar` mostra a mensagem numa caixa.

As abas dependem do perfil: o administrador vê Início, Consultas, Pacientes, Médicos, Contas e Pagamentos. O médico vê Início, Consultas e Pacientes.

Confira antes de apresentar: o login está comentado em `iniciar()`, no fim de janela.py, e o sistema abre como administrador fixo. Religue as linhas comentadas de `TelaLogin` se quiser mostrar o login.

## Perguntas sobre a arquitetura e os fluxos

**1. Por que o sistema tem três camadas?**

Cada camada tem uma tarefa. A tela só lê entradas e mostra resultados, o negócio valida e aplica as regras, e os dados só fazem SQL. Assim cada regra fica em um único lugar e a tela não precisa conhecer o banco.

**2. Por que a tela não chama o DAO direto?**

A validação ficaria misturada com os campos da tela. Trocar a interface obrigaria a reescrever as regras. O serviço também transforma situações como "consulta não encontrada" em erros com mensagem clara.

**3. O que acontece quando um gatilho do banco recusa uma operação?**

A função `transacao()`, em conexao.py, captura o erro do psycopg2 e o transforma em `ErroBanco`, com a mensagem do gatilho. A função `executar` mostra essa mensagem numa caixa. Nada é gravado, porque a transação é desfeita.

**4. Como uma consulta vira realizada e gera a conta?**

Na aba Consultas, o usuário escolhe o status REALIZADA e clica em Aplicar. Abre a `JanelaFinalizarConta`, onde se informa o valor da consulta, o prontuário e os procedimentos. Depois `ContaDAO.finalizar_consulta` faz tudo numa transação: cria a conta, liga à consulta, muda o status e grava os procedimentos.

**5. Por que a conta só nasce na finalização, e não no agendamento?**

O valor depende dos procedimentos realizados e do valor da consulta, que só se conhecem depois do atendimento. No agendamento não há conta nenhuma.

**6. Como funciona o registro de um pagamento?**

O botão Novo Pagamento abre a `JanelaNovoPagamento`. O combo lista as contas que ainda têm saldo. `PagamentoService.registrar` valida o formato dos campos e `PagamentoDAO.inserir` grava. O gatilho 4 confere valores, carteirinha do convênio e saldo da conta.

**7. Como funciona o botão Atendimento da lista de consultas?**

O Treeview não aceita botões dentro das linhas. Nas consultas REALIZADAS, a última coluna mostra o texto "[ Atendimento ]". O método `consulta_do_botao` descobre pela posição do clique (coluna "#8") se o clique foi nele e abre a `JanelaAtendimento`, que edita o prontuário e os procedimentos.

**8. Quem vê o quê na tela inicial?**

O médico vê só as consultas de hoje dele, filtradas por `id_medico`. O administrador vê as de todos os médicos. O filtro está em `ConsultaDAO.listar_de_hoje`.

## Perguntas sobre o banco e os gatilhos

**1. Quais gatilhos existem e o que cada um faz?**

São quatro, em 02_funcoes_gatilhos.sql:

| Gatilho | Quando dispara | O que faz |
| --- | --- | --- |
| trg_valida_conflito_agenda | Antes de gravar ou alterar a consulta | Recusa se o médico ou a sala já têm consulta no mesmo horário. Ignora as canceladas. |
| trg_valida_horario_medico | Antes de gravar ou alterar a consulta | Recusa se o médico não atende naquele dia e hora. |
| trg_atualiza_valor_procedimento_conta | Depois de inserir, alterar ou apagar um procedimento da consulta | Recalcula o valor dos procedimentos da conta. |
| trg_valida_pagamento | Antes de gravar ou alterar o pagamento | Confere valores, carteirinha do convênio e se a soma não passa do total da conta. |

**2. Por que validar no banco e não só no Python?**

O banco é a última barreira: a regra vale para qualquer programa que grave nele. Além disso, o gatilho de pagamento trava a conta com `FOR UPDATE`, e dois pagamentos ao mesmo tempo não conseguem juntos passar do total. O Python valida só o formato e as regras simples.

**3. O gatilho de conflito pega consultas que se sobrepõem, como 14:00 e 14:15?**

Não. Ele compara o horário marcado de forma exata (`data_hora_marcado = NEW.data_hora_marcado`). Duas consultas só conflitam se estiverem marcadas exatamente no mesmo instante.

**4. Como o gatilho de horário sabe o dia da semana?**

Ele converte o número do dia (`EXTRACT(DOW ...)`) em texto, como SEGUNDA ou TERCA. Depois procura em `horario_medico` e `horario` uma faixa do médico com esse dia e com a hora entre início (inclusive) e fim (exclusive). Por isso `dia_semana` deve estar em maiúsculas e sem acento.

**5. Por que `valor_unitario` fica gravado em `consulta_procedimento`?**

Para congelar o preço da época. Se o valor do procedimento mudar no cadastro, as contas antigas continuam com o preço que valia no atendimento. Se `valor_unitario` vier vazio, o gatilho usa o valor do cadastro.

**6. Como o total da conta é calculado?**

`valor_total` é uma coluna gerada: `GENERATED ALWAYS AS (valor_procedimento + valor_consulta) STORED`. O banco calcula sozinho, e ninguém grava esse valor à mão.

**7. Por que a chave de `consulta_procedimento` tem duas colunas?**

A chave é `(id_consulta, id_procedimento)`. Um procedimento aparece uma só vez por consulta. Para repetir, aumenta-se a quantidade.

**8. O que é uma transação e onde o sistema usa?**

É um conjunto de comandos que vale tudo ou nada: se um falha, todos são desfeitos. A função `transacao()` confirma ao sair do bloco sem erro e desfaz se houver erro. `ContaDAO.finalizar_consulta` e `AtendimentoDAO.salvar` rodam vários comandos numa transação só.

**9. O que impede editar os procedimentos de forma que a conta fique menor que o já pago?**

No fim de `AtendimentoDAO.salvar`, o código compara o novo total da conta com a soma dos pagamentos. Se o total ficar menor, lança `ErroBanco`, e a transação desfaz o prontuário e os procedimentos.

## Perguntas sobre o código Python e o Tkinter

**1. O que faz a função `executar` e por que ela recebe uma função sem parênteses?**

Ela chama a função recebida dentro de um `try/except`. Se der `ErroNegocio` ou `ErroBanco`, mostra a mensagem numa caixa e devolve `None`. Sem os parênteses, a função é entregue sem rodar, e quem a chama é o `executar`, já protegido. Com parênteses, ela rodaria antes, fora do `try`.

**2. Por que o código usa funções internas com nome em vez de lambda?**

Um lambda é uma função sem nome, escrita numa linha. Uma função interna com nome faz o mesmo, mas é mais fácil de ler e explica o que está sendo feito. O resultado é igual.

**3. O que significa `self.` dentro das classes?**

`self.algo = valor` guarda o valor dentro do objeto, e todos os métodos da mesma classe passam a poder usá-lo. Uma variável sem `self.` some quando o método termina.

**4. O que significa `class JanelaAtendimento(tk.Toplevel)` e para que serve `super().__init__(pai)`?**

Os parênteses indicam herança: a classe é uma janela do Tkinter e ganha tudo que uma janela tem. O `super().__init__(pai)` chama o construtor da janela básica, que cria a janela dentro da janela `pai`.

**5. Para que serve o parâmetro `ao_salvar` das janelas?**

A aba entrega a função `atualizar` sem parênteses. A janela a guarda e chama `self.ao_salvar()` depois de salvar, para a lista recarregar. A janela não precisa saber nada sobre a aba.

**6. O que é `@contextmanager` e o `yield` da função `transacao`?**

O decorador permite usar a função com `with`. O código antes do `yield` abre a conexão, o `yield` entrega o cursor para o bloco `with`, e o que vem depois fecha a conexão, com sucesso ou com erro.

**7. Por que as camadas do meio não tratam o erro?**

Quando acontece um `raise`, o erro sobe de quem chamou para quem chamou, até encontrar um `try/except`. Aqui isso acontece no `executar`, na tela. Ele captura só `ErroNegocio` e `ErroBanco`. Um bug, como um `KeyError`, passa direto e aparece no terminal.

**8. O que é o `id_de` e por que os combos mostram "12 - Maria"?**

O combo mostra um texto legível com o id na frente. A função `id_de` separa o texto no " - " e devolve o número 12 para ser usado no banco.

**9. O que faz `to_char(c.data_hora_marcado, 'HH24:MI')` nas consultas SQL?**

Converte a data e hora em texto no formato escolhido. `HH24` é a hora de 00 a 23 e `MI` são os minutos, então `2026-11-10 14:30:00` vira `14:30`. Cuidado: `MM` é o mês, não os minutos.

## Desafios de alteração rápida em Python

Cada desafio diz o pedido, onde mexer e como fazer. O caminho é sempre o mesmo: ache a camada certa (tela, negócio ou dados) e altere só ela.

**Desafio 1: mostrar quantas consultas há hoje na tela inicial**

Onde: `AbaInicio`, em janela.py.

```python
# no __init__, logo depois do self.lbl_vazio
self.lbl_quantidade = ttk.Label(card, text="")
self.lbl_quantidade.pack(anchor="e")

# em atualizar, logo depois de preencher(self.tab, consultas)
self.lbl_quantidade.config(text=f"{len(consultas)} consulta(s) hoje")
```

**Desafio 2: esconder as consultas canceladas da tela inicial**

Onde: `ConsultaDAO.listar_de_hoje`, em dao.py. Troque a última linha do começo da consulta SQL:

```python
"WHERE c.data_hora_marcado::date = CURRENT_DATE "
"AND c.status <> 'CANCELADA' ")
```

**Desafio 3: não deixar agendar consulta no passado**

Onde: `AgendaService.agendar`, em agenda.py. A regra é de negócio, então fica no serviço.

```python
from datetime import datetime, timedelta   # no topo: acrescente o datetime

# em agendar, logo depois de calcular dh
if dh < datetime.now():
    raise ErroNegocio("Não é possível agendar uma consulta no passado.")
```

**Desafio 4: preencher a data de hoje no campo Data do agendamento**

Onde: `AbaConsultas.__init__`, em janela.py, logo depois de criar `self.data`.

```python
self.data.insert(0, datetime.now().strftime("%d/%m/%Y"))
```

**Desafio 5: limpar o formulário depois de agendar**

Onde: `AbaConsultas.ao_clicar_agendar`, dentro do `if consulta_id:`.

```python
self.data.delete(0, "end")
self.hora.delete(0, "end")
for combo in self.cb.values():
    combo.set("")
```

**Desafio 6: aceitar no máximo 99 unidades de cada procedimento**

Onde: a validação de quantidade, em servicos.py, nos dois lugares que ela existe: `ContaService.finalizar_consulta` e `AtendimentoService.salvar`.

```python
if quantidade < 1 or quantidade > 99:
    raise ErroNegocio("A quantidade de cada procedimento deve ficar entre 1 e 99.")
```

No `finalizar_consulta` a variável se chama `qtd`, então use esse nome lá.

**Desafio 7: listar as consultas das mais antigas para as mais novas**

Onde: `ConsultaDAO.listar`, em dao.py. Troque o final da consulta SQL:

```python
"ORDER BY c.data_hora_marcado"      # antes: ... DESC
```

**Desafio 8: deixar o prontuário somente leitura na janela de atendimento**

Onde: `JanelaAtendimento.__init__`, no laço que cria as três caixas de texto. O `config` vem depois do `insert`, porque uma caixa desabilitada ignora o `insert`.

```python
caixa.insert("1.0", dados[chave] or "")
caixa.config(state="disabled")
```

## Desafios de alteração rápida no banco

Os gatilhos ficam em 02_funcoes_gatilhos.sql, que pode ser executado de novo: as funções são substituídas e os gatilhos recriados.

**Desafio 1: aceitar a forma de pagamento BOLETO**

São duas mudanças, uma no Python e outra no banco, porque a coluna tem uma restrição `CHECK`. Em servicos.py:

```python
FORMAS_PAGAMENTO = ("CARTAO", "PIX", "DINHEIRO", "BOLETO")
```

No banco (a coluna `VARCHAR(10)` comporta a palavra):

```sql
ALTER TABLE pagamento DROP CONSTRAINT pagamento_forma_pagamento_check;
ALTER TABLE pagamento ADD CONSTRAINT pagamento_forma_pagamento_check
    CHECK (forma_pagamento IN ('CARTAO', 'PIX', 'DINHEIRO', 'BOLETO'));
```

Se o nome da restrição der erro, veja o nome real com `\d pagamento` no psql. A nova forma aparece sozinha no combo do pagamento e no filtro da aba Pagamentos, porque os dois usam `FORMAS_PAGAMENTO`.

**Desafio 2: não aceitar pagamento com data futura**

Onde: função `fn_valida_pagamento`, em 02_funcoes_gatilhos.sql, logo depois da verificação de `NEW.id_conta IS NULL`. A variável `v_data` já existe.

```sql
IF v_data > CURRENT_DATE THEN
    RAISE EXCEPTION 'A data do pagamento não pode ser futura.';
END IF;
```

Depois, execute o arquivo de novo. A mensagem aparece na caixa de erro do sistema.

**Desafio 3: cadastrar um novo horário de atendimento para um médico**

O dia da semana tem que estar em maiúsculas e sem acento, por causa do gatilho de horário. Troque o `1` pelo id do médico.

```sql
WITH novo AS (
    INSERT INTO horario (hora_inicio, hora_fim, dia_semana)
    VALUES ('08:00', '12:00', 'SABADO')
    RETURNING id_horario
)
INSERT INTO horario_medico (id_medico, id_horario)
SELECT 1, id_horario FROM novo;
```

**Desafio 4: mostrar o total pago por forma de pagamento**

```sql
SELECT forma_pagamento, SUM(valor_pago) AS total
FROM pagamento
GROUP BY forma_pagamento
ORDER BY total DESC;
```

**Desafio 5: desligar o gatilho de conflito de agenda**

```sql
DROP TRIGGER IF EXISTS trg_valida_conflito_agenda ON consulta;
```

O `ON consulta` é obrigatório no PostgreSQL. Isso desliga a verificação de médico e a de sala, porque as duas estão na mesma função. Para voltar, execute o arquivo 02_funcoes_gatilhos.sql de novo.
