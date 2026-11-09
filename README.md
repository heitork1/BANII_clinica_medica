# Sistema de Clínica Médica (Tema 2) – BD II / UDESC

Aplicação em Python (POO) com três camadas:

| Camada | Pasta | Papel |
| Apresentação: `apresentacao/` -> Interface Tkinter: cadastro e consulta.
| Negócio: `negocio/` -> Modelos, validações (CPF, datas, valores) e serviços.
| Dados: `dados/` ->  Conexão/transação e DAOs com SQL (psycopg2).

As funcionalidades: 

Consultar pagamentos (aba Pagamentos, com filtros por período, forma, convênio, paciente e médico), cadastrar/buscar pacientes (com telefones e, opcionalmente, a carteirinha do convênio), cadastrar/listar médicos (especialidades e horários).

Agendar consultas e alterar o status. Ao marcar uma consulta como REALIZADA abre-se a janela de finalização (valor da consulta e procedimentos realizados) e a conta da consulta é gerada; as contas ficam na aba Contas e são quitadas na aba Pagamentos. 

Conflitos de agenda e horário do médico são barrados pelos gatilhos do banco e a mensagem aparece na tela.

## Como executar
1. Crie o banco: `createdb clinica`
2. Rode em ordem: `sql/01_esquema.sql`, `sql/02_funcoes_gatilhos.sql`, `sql/03_dados_exemplo.sql`
   (ex.: `psql -d clinica -f sql/01_esquema.sql`)
3. `pip install -r requirements.txt`
4. (opcional) variáveis `PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD`
5. `python main.py`

Ordem para testar: cadastre convênios e procedimentos direto no banco; cadastre um médico (com especialidade e horários), um paciente e somente então agende a consulta.

