# Sistema de Clínica Médica (Tema 2) – BD II / UDESC

Aplicação em Python (POO) com três camadas:

| Camada | Pasta | Papel |
|---|---|---|
| Apresentação | `apresentacao/` | Interface Tkinter: cadastro e consulta |
| Negócio | `negocio/` | Modelos, validações (CPF, datas, valores) e serviços; `agenda.py` define `DURACAO_CONSULTA` |
| Dados | `dados/` | Conexão/transação e DAOs com SQL (psycopg2) |

Funcionalidades: consultar pagamentos (aba Pagamentos, com filtros por período, forma, convênio, paciente e médico), cadastrar/buscar pacientes (com telefones), cadastrar/listar médicos (especialidades e horários),
agendar consultas (cria a conta junto) e alterar o status. Conflitos de agenda e horário do médico são
barrados pelos gatilhos do banco e a mensagem aparece na tela.

## Como executar
1. Crie o banco: `createdb clinica`
2. Rode em ordem: `sql/01_esquema.sql`, `sql/02_funcoes_gatilhos.sql`, `sql/03_dados_exemplo.sql`
   (ex.: `psql -d clinica -f sql/01_esquema.sql`)
3. `pip install -r requirements.txt`
4. (opcional) variáveis `PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD`
5. `python main.py`

Ordem de uso: cadastre um médico (com horários), um paciente e então agende a consulta.


Tutorial de Tkinter:
https://www.pythontutorial.net/tkinter/
