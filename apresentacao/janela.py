"""Camada de apresentação (Tkinter): só captura entradas e exibe resultados."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from dados.conexao import ErroBanco
from negocio.agenda import AgendaService, STATUS
from negocio.servicos import MedicoService, PacienteService, ServicoAutenticacao
from negocio.validacao import ErroNegocio


PERMISSOES = {
    "ADMIN": ["Início", "Consultas", "Pacientes", "Médicos", "Convênios", "Especialidades", "Procedimentos", "Salas", "Usuários"],
    "RECEPCAO": ["Início", "Consultas", "Pacientes", "Médicos", "Convênios"],
    "MEDICO": ["Início", "Consultas", "Pacientes"]
}


def executar(acao):
    """Roda uma ação e mostra erros de negócio/banco numa caixa de mensagem."""
    try:
        return acao()
    except (ErroNegocio, ErroBanco) as e:
        messagebox.showerror("Atenção", str(e))
    return None


def tabela(pai, colunas, larguras):
    t = ttk.Treeview(pai, columns=colunas, show="headings", height=10)
    for c, w in zip(colunas, larguras):
        t.heading(c, text=c)
        t.column(c, width=w)
    t.pack(fill="both", expand=True, padx=6, pady=6)
    return t


def preencher(t, linhas):
    t.delete(*t.get_children())
    for l in linhas:
        t.insert("", "end", values=["" if v is None else v for v in l])


def campo(pai, rotulo, linha, largura=30):
    ttk.Label(pai, text=rotulo).grid(row=linha, column=0, sticky="e", padx=4, pady=2)
    e = ttk.Entry(pai, width=largura)
    e.grid(row=linha, column=1, sticky="w", pady=2)
    return e


def id_de(texto):
    return int(texto.split(" - ")[0]) if texto else None

class AbaInicio(ttk.Frame):
    def __init__(self, pai):
            super().__init__(pai)
            self.pai = pai

            hoje = datetime.now()
            dia_extenso = f"{hoje.day}/{hoje.month}/{hoje.year}"

            saudacao = "Bom dia!" if hoje.hour < 12 else ("Boa tarde!" if hoje.hour < 18 else "Boa noite!")
            topo = ttk.Frame(self)
            topo.pack(fill="x", padx=16, pady=(16,12))

            lbl_saudacao = ttk.Frame(topo)
            lbl_saudacao.pack(side="left")
            ttk.Label(lbl_saudacao, text=saudacao, font=("Helvetica", 15, "bold")).pack(anchor="w")
            ttk.Label(lbl_saudacao, text=dia_extenso, font=("Helvetica", 10), foreground="#666666").pack(anchor="w", pady=(2,0))

            botoes_topo = ttk.Frame(topo)
            botoes_topo.pack(side="right")

            ttk.Button(botoes_topo, text="+ Novo paciente", command=lambda: self.pai.select(2)).pack(side="left", padx=4)
            ttk.Button(botoes_topo, text="+ Nova consulta", command=lambda: self.pai.select(1)).pack(side="left", padx=4)

            ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=8) 

            card = ttk.LabelFrame(self, text="Consultas de hoje ", padding=14)
            card.pack(fill="x", padx=16, pady=10)

            card_topo = ttk.Frame(card)
            card_topo.pack(fill="x", pady=(0,10))

            ttk.Label(card_topo, text="Resumo do dia", font=("Helvetica", 10, "bold")).pack(side="left")
            ttk.Button(card_topo, text="Abrir agenda →", command=lambda: self.pai.select(1)).pack(side="right")

            corpo_vazio = ttk.Frame(card)
            corpo_vazio.pack(fill="both", expand=True, pady=25)

            ttk.Label(
                corpo_vazio,
                text="Nenhuma consulta marcada para hoje",
                font=("Helvetica", 10, "italic"),
                foreground="#555555"
            ).pack(pady=(0,10))

            ttk.Button(corpo_vazio, text="Marcar consulta", command=lambda: self.pai.select(1)).pack()
                

class AbaPacientes(ttk.Frame):
    def __init__(self, pai):
        super().__init__(pai)
        self.svc = PacienteService()
        f = ttk.LabelFrame(self, text="Novo paciente")
        f.pack(fill="x", padx=6, pady=6)
        self.nome = campo(f, "Nome*", 0, 40)
        self.cpf = campo(f, "CPF*", 1)
        self.nasc = campo(f, "Nascimento (DD/MM/AAAA)", 2, 15)
        self.rg = campo(f, "RG", 3, 20)
        ttk.Label(f, text="Sexo").grid(row=4, column=0, sticky="e", padx=4)
        self.sexo = ttk.Combobox(f, values=["Feminino", "Masculino", "Outro"], width=15, state="readonly")
        self.sexo.grid(row=4, column=1, sticky="w")
        self.end = campo(f, "Endereço", 5, 50)
        self.email = campo(f, "E-mail", 6, 35)
        self.tels = campo(f, "Telefones (separe por vírgula)", 7, 35)
        ttk.Button(f, text="Cadastrar", command=self.cadastrar).grid(row=8, column=1, sticky="w", pady=4)

        b = ttk.Frame(self)
        b.pack(fill="x", padx=6)
        ttk.Label(b, text="Buscar (nome ou CPF):").pack(side="left")
        self.busca = ttk.Entry(b, width=25)
        self.busca.pack(side="left", padx=4)
        ttk.Button(b, text="Buscar", command=self.atualizar).pack(side="left")
        self.tab = tabela(self, ("ID", "Nome", "CPF", "Nascimento", "E-mail", "Telefones"),
                          (40, 200, 110, 90, 180, 150))
        self.atualizar()

    def cadastrar(self):
        r = executar(lambda: self.svc.cadastrar(
            self.nome.get(), self.cpf.get(), self.nasc.get(), self.rg.get(), self.sexo.get(),
            self.end.get(), self.email.get(), self.tels.get()))
        if r:
            for e in (self.nome, self.cpf, self.nasc, self.rg, self.end, self.email, self.tels):
                e.delete(0, "end")
            messagebox.showinfo("Pronto", "Paciente cadastrado.")
            self.atualizar()

    def atualizar(self):
        l = executar(lambda: self.svc.listar(self.busca.get()))
        if l is not None:
            preencher(self.tab, l)


class AbaMedicos(ttk.Frame):
    def __init__(self, pai):
        super().__init__(pai)
        self.svc = MedicoService()
        self.esp, self.hor = [], []
        f = ttk.LabelFrame(self, text="Novo médico")
        f.pack(fill="x", padx=6, pady=6)
        self.nome = campo(f, "Nome*", 0, 40)
        self.crm = campo(f, "CRM*", 1, 20)
        self.pct = campo(f, "Honorário (%)*", 2, 10)
        self.tel = campo(f, "Telefone", 3, 20)
        ttk.Label(f, text="Especialidades*").grid(row=0, column=2, padx=8)
        self.lb_esp = tk.Listbox(f, selectmode="multiple", height=5, exportselection=False, width=28)
        self.lb_esp.grid(row=1, column=2, rowspan=3, padx=8)
        ttk.Label(f, text="Horários de atendimento").grid(row=0, column=3, padx=8)
        self.lb_hor = tk.Listbox(f, selectmode="multiple", height=5, exportselection=False, width=30)
        self.lb_hor.grid(row=1, column=3, rowspan=3, padx=8)
        ttk.Button(f, text="Cadastrar", command=self.cadastrar).grid(row=4, column=1, sticky="w", pady=4)
        self.tab = tabela(self, ("ID", "Nome", "CRM", "%", "Especialidades", "Horários"),
                          (40, 160, 90, 50, 180, 380))
        self.atualizar()

    def atualizar(self):
        def carregar():
            self.esp = self.svc.especialidades()
            self.hor = self.svc.horarios()
            return self.svc.listar()
        l = executar(carregar)
        if l is None:
            return
        self.lb_esp.delete(0, "end")
        self.lb_hor.delete(0, "end")
        for _, n in self.esp:
            self.lb_esp.insert("end", n)
        for _, n in self.hor:
            self.lb_hor.insert("end", n)
        preencher(self.tab, l)

    def cadastrar(self):
        esp = [self.esp[i][0] for i in self.lb_esp.curselection()]
        hor = [self.hor[i][0] for i in self.lb_hor.curselection()]
        r = executar(lambda: self.svc.cadastrar(self.nome.get(), self.crm.get(), self.pct.get(),
                                                self.tel.get(), esp, hor))
        if r:
            for e in (self.nome, self.crm, self.pct, self.tel):
                e.delete(0, "end")
            messagebox.showinfo("Pronto", "Médico cadastrado.")
            self.atualizar()


class AbaConsultas(ttk.Frame):
    def __init__(self, pai):
        super().__init__(pai)
        self.agenda = AgendaService()
        self.pac = PacienteService()
        self.med = MedicoService()
        f = ttk.LabelFrame(self, text="Agendar consulta")
        f.pack(fill="x", padx=6, pady=6)
        self.cb = {}
        for i, nome in enumerate(("Paciente", "Médico", "Sala")):
            ttk.Label(f, text=nome + "*").grid(row=i, column=0, sticky="e", padx=4, pady=2)
            c = ttk.Combobox(f, width=45, state="readonly")
            c.grid(row=i, column=1, sticky="w")
            self.cb[nome] = c
        self.dh = campo(f, "Data e hora* (DD/MM/AAAA HH:MM)", 3, 20)
        self.valor = campo(f, "Valor da consulta (R$)*", 4, 12)
        ttk.Button(f, text="Agendar", command=self.agendar).grid(row=5, column=1, sticky="w", pady=4)

        b = ttk.Frame(self)
        b.pack(fill="x", padx=6)
        ttk.Label(b, text="Mudar status da consulta selecionada:").pack(side="left")
        self.st = ttk.Combobox(b, values=STATUS, width=14, state="readonly")
        self.st.pack(side="left", padx=4)
        ttk.Button(b, text="Aplicar", command=self.mudar_status).pack(side="left")
        ttk.Button(b, text="Atualizar listas", command=self.atualizar).pack(side="right")
        self.tab = tabela(self, ("ID", "Data/hora", "Paciente", "Médico", "Sala", "Status", "Total R$"),
                          (40, 120, 170, 170, 150, 90, 80))
        self.atualizar()

    def atualizar(self):
        def carregar():
            return (self.pac.opcoes(), self.med.opcoes(), self.med.salas_opcoes(), self.agenda.listar())
        r = executar(carregar)
        if r is None:
            return
        for nome, dados in zip(("Paciente", "Médico", "Sala"), r[:3]):
            self.cb[nome]["values"] = [f"{i} - {n}" for i, n in dados]
        preencher(self.tab, r[3])

    def agendar(self):
        r = executar(lambda: self.agenda.agendar(
            id_de(self.cb["Paciente"].get()), id_de(self.cb["Médico"].get()),
            id_de(self.cb["Sala"].get()), self.dh.get(), self.valor.get()))
        if r:
            messagebox.showinfo("Pronto", "Consulta agendada.")
            self.atualizar()

    def mudar_status(self):
        sel = self.tab.selection()
        if not sel or not self.st.get():
            messagebox.showwarning("Atenção", "Selecione uma consulta e um status.")
            return
        id_c = int(self.tab.item(sel[0])["values"][0])
        executar(lambda: self.agenda.mudar_status(id_c, self.st.get()))
        self.atualizar()

class AbaConvenios(ttk.Frame):
    def __init__(self, pai):
            super().__init__(pai)

class AbaEspecialidades(ttk.Frame):
    def __init__(self, pai):
            super().__init__(pai)

class AbaProcedimentos(ttk.Frame):
    def __init__(self, pai):
            super().__init__(pai)

class AbaSalas(ttk.Frame):
    def __init__(self, pai):
            super().__init__(pai)

class AbaUsuarios(ttk.Frame):
    def __init__(self, pai):
            super().__init__(pai)


class TelaLogin(ttk.Frame):
    def __init__(self, pai, on_sucesso):
        super().__init__(pai)
        self.on_sucesso = on_sucesso  
        self.auth = ServicoAutenticacao()

        centro = ttk.Frame(self)
        centro.pack(expand=True)

        ttk.Label(centro, text="Clínica Médica", font=("Helvetica", 16, "bold")).pack(pady=(0, 16))

        ttk.Label(centro, text="E-mail").pack(anchor="w")
        self.email = ttk.Entry(centro, width=30)
        self.email.pack(pady=(0, 10))
        self.email.focus()

        ttk.Label(centro, text="Senha").pack(anchor="w")
        self.senha = ttk.Entry(centro, width=30, show="*")
        self.senha.pack(pady=(0, 16))
        self.senha.bind("<Return>", lambda e: self.entrar())

        ttk.Button(centro, text="Entrar", command=self.entrar).pack(fill="x")

    def entrar(self):
        usuario = executar(lambda: self.auth.entrar(self.email.get(), self.senha.get()))
        if usuario:
            self.on_sucesso(usuario)

def iniciar():
    raiz = tk.Tk()
    raiz.title("Clínica Médica")
    raiz.geometry("1000x640")

    estilo = ttk.Style()
    # estilo.theme_use("clam")
    estilo.configure("TNotebook", tabposition="wn")
    estilo.configure("TNotebook.Tab", padding=[15,8], font=("Helvetica", 10), width=15, anchor="w")
    estilo.map("TNotebook.Tab", background=[
        ("selected", 
         "#3A3A3A"),
        ("!selected",
         "#E0E0E0")],
         
    )
    def abrir_sistema(usuario):
        login.destroy() 
        raiz.title(f"Clínica Médica - {usuario['nome']} ({usuario['perfil']})")

        nb = ttk.Notebook(raiz)
        nb.pack(fill="both", expand=True)

        nb.add(AbaInicio(nb), text="Início")
        nb.add(AbaConsultas(nb), text="Consultas")
        nb.add(AbaPacientes(nb), text="Pacientes")
        nb.add(AbaMedicos(nb), text="Médicos")
        nb.add(AbaConvenios(nb), text="Convênios")
        nb.add(AbaEspecialidades(nb), text="Especialidades")
        nb.add(AbaProcedimentos(nb), text="Procedimentos")
        nb.add(AbaSalas(nb), text="salas")
        nb.add(AbaUsuarios(nb), text="Usuarios")

    login = TelaLogin(raiz, abrir_sistema)
    login.pack(fill="both", expand=True)

    raiz.mainloop()
