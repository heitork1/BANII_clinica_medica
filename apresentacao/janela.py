import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from dados.conexao import ErroBanco
from negocio.agenda import AgendaService, STATUS
from negocio.servicos import (MedicoService, PacienteService, PagamentoService, ContaService, AtendimentoService,
                              FORMAS_PAGAMENTO, SITUACOES_CONTA, ServicoAutenticacao)
from negocio.validacao import ErroNegocio

PERMISSOES = {
    "ADMIN": ["Início", "Consultas", "Pacientes", "Médicos", "Contas", "Pagamentos"],
    "MEDICO": ["Início", "Consultas", "Pacientes"]
}

def executar(acao):
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


def moeda(valor):
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def id_de(texto):
    return int(texto.split(" - ")[0]) if texto else None


class AbaInicio(ttk.Frame):

    def __init__(self, pai):
        super().__init__(pai, style="Verde.TFrame")
        hoje = datetime.now()
        saudacao = "Bom dia!" if hoje.hour < 12 else ("Boa tarde!" if hoje.hour < 18 else "Boa noite!")
        centro = ttk.Frame(self, style="Verde.TFrame")
        centro.pack(expand=True)
        ttk.Label(centro, text=saudacao, font=("Helvetica", 22, "bold"), style="VerdeTitulo.TLabel").pack()
        ttk.Label(centro, text=f"{hoje.day}/{hoje.month}/{hoje.year}", font=("Helvetica", 11),
                  style="Verde.TLabel", foreground="#5F7A6A").pack(pady=(2, 16))
        ttk.Label(centro, text="Bem-vindo(a) à Clínica CCT", font=("Helvetica", 14), style="Verde.TLabel").pack()


class AbaPacientes(ttk.Frame):
    NENHUM = "Nenhum"

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

       

        cv = ttk.LabelFrame(f, text="Convênio (opcional)")
        cv.grid(row=0, column=2, rowspan=5, sticky="n", padx=16)
        ttk.Label(cv, text="Convênio").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.cb_conv = ttk.Combobox(cv, width=22, state="readonly")
        self.cb_conv.grid(row=0, column=1, sticky="w", pady=2)
        self.cb_conv.bind("<<ComboboxSelected>>", lambda e: self.ajustar_convenio())
        self.carteirinha = campo(cv, "Nº da carteirinha*", 1, 25)
        self.validade = campo(cv, "Validade (DD/MM/AAAA)", 2, 15)
        self.plano = campo(cv, "Tipo de plano", 3, 25)
        self.carregar_convenios()

        b = ttk.Frame(self)
        b.pack(fill="x", padx=6)
        ttk.Label(b, text="Buscar (nome ou CPF):").pack(side="left")
        self.busca = ttk.Entry(b, width=25)
        self.busca.pack(side="left", padx=4)
        ttk.Button(b, text="Buscar", command=self.atualizar).pack(side="left")
        self.tab = tabela(self, ("ID", "Nome", "CPF", "Nascimento", "E-mail", "Telefones", "Convênio"),
                          (40, 170, 110, 85, 150, 120, 170))
        self.atualizar()

    def carregar_convenios(self):
        convenios = executar(self.svc.convenios) or []
        atual = self.cb_conv.get()
        self.cb_conv["values"] = [self.NENHUM] + [f"{i} - {n}" for i, n in convenios]
        self.cb_conv.set(atual if atual in self.cb_conv["values"] else self.NENHUM)
        self.ajustar_convenio()

    def ajustar_convenio(self):
        tem = self.cb_conv.get() != self.NENHUM
        for e in (self.carteirinha, self.validade, self.plano):
            e.config(state="normal")
            if not tem:
                e.delete(0, "end")
                e.config(state="disabled")

    def ao_exibir(self):
        self.carregar_convenios()

    def cadastrar(self):
        def chamar_servico():

            return self.svc.cadastrar(
                self.nome.get(), self.cpf.get(), self.nasc.get(), self.rg.get(), self.sexo.get(),
                self.end.get(), self.email.get(), self.tels.get(),
                None if self.cb_conv.get() == self.NENHUM else id_de(self.cb_conv.get()),
                self.carteirinha.get(), self.validade.get(), self.plano.get())

        paciente_id = executar(chamar_servico)
        if paciente_id:
            for e in (self.nome, self.cpf, self.nasc, self.rg, self.end, self.email, self.tels):
                e.delete(0, "end")
            self.cb_conv.set(self.NENHUM)
            self.ajustar_convenio()
            messagebox.showinfo("Pronto", "Paciente cadastrado.")
            self.atualizar()

    def atualizar(self):
        def buscar_pacientes():
            return self.svc.listar(self.busca.get())

        pacientes = executar(buscar_pacientes)
        if pacientes is not None:
            preencher(self.tab, pacientes)


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
        ttk.Label(f, text="Horários de atendimento*").grid(row=0, column=3, padx=8)
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

        def chamar_servico():

            return self.svc.cadastrar(self.nome.get(), self.crm.get(), self.pct.get(),
                                      self.tel.get(), esp, hor)

        medico_id = executar(chamar_servico)
        if medico_id:
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
        self.data = campo(f, "Data* (DD/MM/AAAA)", 3, 12)
        self.hora = campo(f, "Hora* (HH:MM)", 4, 8)
        ttk.Button(f, text="Agendar", command=self.ao_clicar_agendar).grid(row=5, column=1, sticky="w", pady=4)


        self.lbl_horarios = ttk.Label(f, text="Selecione um médico para ver os horários.", justify="left")
        self.lbl_horarios.grid(row=0, column=2, rowspan=5, sticky="nw", padx=20)
        self.cb["Médico"].bind("<<ComboboxSelected>>", self.ao_escolher_medico)

        b = ttk.Frame(self)
        b.pack(fill="x", padx=6)
        ttk.Label(b, text="Mudar status da consulta selecionada:").pack(side="left")
        self.st = ttk.Combobox(b, values=STATUS, width=14, state="readonly")
        self.st.pack(side="left", padx=4)
        ttk.Button(b, text="Aplicar", command=self.mudar_status).pack(side="left")
        ttk.Button(b, text="Atualizar listas", command=self.atualizar).pack(side="right")

        self.tab = tabela(self, ("ID", "Data/hora", "Paciente", "Médico", "Sala", "Status", "Total R$", ""),
                          (40, 100, 140, 140, 150, 90, 80, 110))
        self.tab.bind("<Button-1>", self.ao_clicar_na_tabela)
        self.tab.bind("<Motion>", self.ao_mover_o_mouse)
        self.atualizar()

    def ao_escolher_medico(self, evento):
        id_medico = id_de(self.cb["Médico"].get())

        def buscar_horarios():
            return self.med.horarios_do_medico(id_medico)

        texto = executar(buscar_horarios)
        if texto is not None:
            self.lbl_horarios.config(text=texto)

    def consulta_do_botao(self, evento):
        linha = self.tab.identify_row(evento.y)
        coluna = self.tab.identify_column(evento.x)
        if not linha or coluna != "#8":
            return None
        valores = self.tab.item(linha)["values"]
        if valores[5] != "REALIZADA":
            return None
        return int(valores[0])

    def ao_clicar_na_tabela(self, evento):
        id_consulta = self.consulta_do_botao(evento)
        if id_consulta:
            JanelaAtendimento(self, id_consulta, self.atualizar)

    def ao_mover_o_mouse(self, evento):
        if self.consulta_do_botao(evento):
            self.tab.config(cursor="hand2")
        else:
            self.tab.config(cursor="")


    def atualizar(self):
        def carregar():
            return (self.pac.opcoes(), self.med.opcoes(), self.med.salas_opcoes(), self.agenda.listar())
        r = executar(carregar)
        if r is None:
            return
        for nome, dados in zip(("Paciente", "Médico", "Sala"), r[:3]):
            self.cb[nome]["values"] = [f"{i} - {n}" for i, n in dados]
        preencher(self.tab, r[3])
        self.criar_botao_atendimento()

    def criar_botao_atendimento(self):
        for item in self.tab.get_children():
            valores = list(self.tab.item(item)["values"])
            if valores[5] == "REALIZADA":
                valores = valores[:7] + ["[ Atendimento ]"]
                self.tab.item(item, values=valores)

    def ao_clicar_agendar(self):

        id_paciente = id_de(self.cb["Paciente"].get())
        id_medico = id_de(self.cb["Médico"].get())
        id_sala = id_de(self.cb["Sala"].get())

        def chamar_servico():

            return self.agenda.agendar(id_paciente, id_medico, id_sala, self.data.get(), self.hora.get())


        consulta_id = executar(chamar_servico)
        if consulta_id:
            messagebox.showinfo("Pronto", "Consulta agendada.")
            self.atualizar()

    def mudar_status(self):
        sel = self.tab.selection()
        if not sel or not self.st.get():
            messagebox.showwarning("Atenção", "Selecione uma consulta e um status.")
            return
        valores = self.tab.item(sel[0])["values"]

        id_c = int(valores[0])
        novo_status = self.st.get()

        if novo_status == "REALIZADA":

            if valores[5] == "REALIZADA":
                messagebox.showwarning("Atenção", "Esta consulta já foi realizada e a conta já foi gerada.")
                return
            resumo = f"Consulta {id_c} - {valores[2]} com {valores[3]} ({valores[1]})"
            JanelaFinalizarConta(self, id_c, resumo, self.atualizar)
            return

        def chamar_servico():
            self.agenda.mudar_status(id_c, novo_status)

        executar(chamar_servico)
        self.atualizar()

class JanelaAtendimento(tk.Toplevel):

    def __init__(self, pai, id_consulta, ao_salvar):
        super().__init__(pai)
        self.svc = AtendimentoService()
        self.id_consulta = id_consulta
        self.ao_salvar = ao_salvar   
        self.catalogo = {}           
        self.itens = {}             

        def buscar_dados():
            return self.svc.buscar(id_consulta)

        dados = executar(buscar_dados)
        if dados is None:
            self.destroy()
            return

        self.title("Atendimento")
        self.transient(pai.winfo_toplevel())
        self.grab_set()

        f = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=12, pady=12)
        resumo = f"Consulta {id_consulta} - {dados['paciente']} com {dados['medico']} ({dados['data_hora']})"
        ttk.Label(f, text=resumo, font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))


        self.txt = {}
        for i, (chave, rotulo) in enumerate((("sintomas", "Sintomas"), ("diagnostico", "Diagnóstico"),
                                             ("prescricao", "Prescrição")), start=1):
            ttk.Label(f, text=rotulo).grid(row=i, column=0, sticky="ne", padx=4, pady=2)
            caixa = tk.Text(f, width=55, height=3 )
            caixa.insert("1.0", dados[chave] or "")
            caixa.config(state="disabled")
            caixa.grid(row=i, column=1, sticky="w", pady=2)
            self.txt[chave] = caixa


        proc = ttk.LabelFrame(f, text="Procedimentos realizados")
        proc.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        linha = ttk.Frame(proc)

        self.cb_proc = ttk.Combobox(linha, width=48, state="readonly")

        self.tab = tabela(proc, ("Procedimento", "Qtd", "Valor unit.", "Subtotal"), (280, 50, 90, 90))
        self.tab.configure(height=5)
        ttk.Button(proc, text="Remover selecionado", command=self.remover).pack(anchor="e", padx=6, pady=(0, 6))

        self.lbl_total = ttk.Label(f, text="", font=("Helvetica", 11, "bold"))
        self.lbl_total.grid(row=5, column=0, columnspan=2, sticky="e", pady=(8, 0))

        botoes = ttk.Frame(f)
        botoes.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(botoes, text="Fechar", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(botoes, text="Salvar", command=self.salvar).pack(side="left")


        lista = executar(ContaService().procedimentos) or []
        for p in lista:
            self.catalogo[p["id_procedimento"]] = p
        self.cb_proc["values"] = [f"{p['id_procedimento']} - {p['descricao']} ({moeda(p['valor'])})"
                                  for p in lista]
        for p in dados["procedimentos"]:

            self.itens[p["id_procedimento"]] = {"descricao": p["descricao"], "quantidade": p["quantidade"],
                                                "valor": p["valor_unitario"]}
        self.redesenhar()

    def adicionar(self):
        if not self.cb_proc.get():
            messagebox.showwarning("Atenção", "Escolha um procedimento.", parent=self)
            return
        try:
            qtd = int(self.qtd.get())
            if qtd < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Atenção", "Informe uma quantidade inteira maior que zero.", parent=self)
            return
        id_p = id_de(self.cb_proc.get())
        if id_p in self.itens:

            self.itens[id_p]["quantidade"] += qtd
        else:
            p = self.catalogo[id_p]
            self.itens[id_p] = {"descricao": p["descricao"], "quantidade": qtd, "valor": p["valor"]}
        self.qtd.set(1)
        self.redesenhar()

    def remover(self):
        sel = self.tab.selection()
        if not sel:
            return
        id_p = list(self.itens)[self.tab.index(sel[0])]
        del self.itens[id_p]
        self.redesenhar()

    def redesenhar(self):
        linhas = []
        total = 0
        for i in self.itens.values():
            subtotal = float(i["valor"]) * i["quantidade"]
            total += subtotal
            linhas.append((i["descricao"], i["quantidade"], moeda(i["valor"]), moeda(subtotal)))
        preencher(self.tab, linhas)
        self.lbl_total.config(text=f"Total dos procedimentos: {moeda(total)}")

    def salvar(self):
        def texto(chave):
            return self.txt[chave].get("1.0", "end").strip()

        itens = [(id_p, i["quantidade"], i["valor"]) for id_p, i in self.itens.items()]

        def chamar_servico():
            self.svc.salvar(self.id_consulta, texto("sintomas"), texto("diagnostico"),
                            texto("prescricao"), itens)
            return True

        if executar(chamar_servico):
            messagebox.showinfo("Pronto", "Atendimento salvo.", parent=self)
            self.ao_salvar()
            self.destroy()


class JanelaFinalizarConta(tk.Toplevel):

    def __init__(self, pai, id_consulta, resumo, ao_finalizar):
        super().__init__(pai)
        self.title("Finalizar consulta e gerar conta")
        self.transient(pai.winfo_toplevel())
        self.grab_set()
        self.svc = ContaService()
        self.id_consulta = id_consulta
        self.ao_finalizar = ao_finalizar
        self.catalogo = {}
        self.itens = {}

        f = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(f, text=resumo, font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.valor_consulta = campo(f, "Valor da consulta (R$)*", 1, 15)
        self.valor_consulta.bind("<KeyRelease>", lambda e: self.atualizar_total())


        self.txt = {}
        for i, (chave, rotulo) in enumerate((("sintomas", "Sintomas"), ("diagnostico", "Diagnóstico"),
                                             ("prescricao", "Prescrição")), start=2):
            ttk.Label(f, text=rotulo).grid(row=i, column=0, sticky="ne", padx=4, pady=2)
            caixa = tk.Text(f, width=55, height=2)
            caixa.grid(row=i, column=1, sticky="w", pady=2)
            self.txt[chave] = caixa

        proc = ttk.LabelFrame(f, text="Procedimentos realizados")
        proc.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        linha = ttk.Frame(proc)
        linha.pack(fill="x", padx=6, pady=6)
        self.cb_proc = ttk.Combobox(linha, width=48, state="readonly")
        self.cb_proc.pack(side="left")
        ttk.Label(linha, text="Qtd").pack(side="left", padx=(10, 2))
        self.qtd = ttk.Spinbox(linha, from_=1, to=999, width=5)
        self.qtd.set(1)
        self.qtd.pack(side="left")
        ttk.Button(linha, text="Adicionar", command=self.adicionar).pack(side="left", padx=6)

        self.tab = tabela(proc, ("Procedimento", "Qtd", "Valor unit.", "Subtotal"), (280, 50, 90, 90))
        self.tab.configure(height=5)
        ttk.Button(proc, text="Remover selecionado", command=self.remover).pack(anchor="e", padx=6, pady=(0, 6))

        self.lbl_total = ttk.Label(f, text="", font=("Helvetica", 11, "bold"))
        self.lbl_total.grid(row=6, column=0, columnspan=2, sticky="e", pady=(8, 0))

        botoes = ttk.Frame(f)
        botoes.grid(row=7, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(botoes, text="Cancelar", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(botoes, text="Finalizar", command=self.finalizar).pack(side="left")

        self.carregar_procedimentos()
        self.atualizar_total()

    def carregar_procedimentos(self):
        lista = executar(self.svc.procedimentos)
        for p in lista or []:
            self.catalogo[p["id_procedimento"]] = p
        self.cb_proc["values"] = [f"{p['id_procedimento']} - {p['descricao']} ({moeda(p['valor'])})"
                                  for p in (lista or [])]

    def adicionar(self):
        if not self.cb_proc.get():
            messagebox.showwarning("Atenção", "Escolha um procedimento.", parent=self)
            return
        try:
            qtd = int(self.qtd.get())
            if qtd < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Atenção", "Informe uma quantidade inteira maior que zero.", parent=self)
            return
        id_p = id_de(self.cb_proc.get())

        self.itens[id_p] = self.itens.get(id_p, 0) + qtd
        self.qtd.set(1)
        self.redesenhar()

    def remover(self):
        sel = self.tab.selection()
        if not sel:
            return
        id_p = list(self.itens)[self.tab.index(sel[0])]
        del self.itens[id_p]
        self.redesenhar()

    def redesenhar(self):
        linhas = []
        for id_p, qtd in self.itens.items():
            p = self.catalogo[id_p]
            linhas.append((p["descricao"], qtd, moeda(p["valor"]), moeda(float(p["valor"]) * qtd)))
        preencher(self.tab, linhas)
        self.atualizar_total()

    def atualizar_total(self):
        try:
            consulta = float(self.valor_consulta.get().strip().replace(",", ".") or 0)
        except ValueError:
            consulta = 0
        procedimentos = sum(float(self.catalogo[i]["valor"]) * q for i, q in self.itens.items())
        self.lbl_total.config(
            text=f"Consulta {moeda(consulta)} + procedimentos {moeda(procedimentos)} = {moeda(consulta + procedimentos)}")

    def finalizar(self):
        def texto(chave):
            return self.txt[chave].get("1.0", "end").strip()

        def chamar_servico():
            return self.svc.finalizar_consulta(
                self.id_consulta, self.valor_consulta.get(), texto("sintomas"), texto("diagnostico"),
                texto("prescricao"), list(self.itens.items()))

        id_conta = executar(chamar_servico)
        if id_conta:
            messagebox.showinfo("Pronto", f"Consulta finalizada. Conta nº {id_conta} gerada.", parent=self)
            self.ao_finalizar()
            self.destroy()


class AbaContas(ttk.Frame):
    TODAS = "Todas"

    def __init__(self, pai):
        super().__init__(pai)
        self.svc = ContaService()

        topo = ttk.Frame(self)
        topo.pack(fill="x", padx=6, pady=6)
        ttk.Label(topo, text="Situação:").pack(side="left")
        self.situacao = ttk.Combobox(topo, values=[self.TODAS, *SITUACOES_CONTA], width=14, state="readonly")
        self.situacao.set(self.TODAS)
        self.situacao.pack(side="left", padx=4)
        self.situacao.bind("<<ComboboxSelected>>", lambda e: self.atualizar())
        ttk.Button(topo, text="Atualizar", command=self.atualizar).pack(side="left", padx=4)

        self.tab = tabela(self, ("Conta", "Consulta", "Realizada em", "Paciente", "Médico", "Consulta R$",
                                 "Procedim. R$", "Total R$", "Pago R$", "Saldo R$", "Situação"),
                          (50, 65, 115, 150, 150, 85, 90, 80, 80, 80, 80))
        self.lbl_total = ttk.Label(self, text="", font=("Helvetica", 10, "bold"))
        self.lbl_total.pack(anchor="e", padx=10, pady=(0, 6))
        self.atualizar()

    def ao_exibir(self):
        self.atualizar()

    def atualizar(self):
        def buscar_contas():
            return self.svc.listar("" if self.situacao.get() == self.TODAS else self.situacao.get())

        linhas = executar(buscar_contas)
        if linhas is None:
            return
        preencher(self.tab, linhas)
        total, pago, saldo = self.svc.totais(linhas)
        self.lbl_total.config(text=f"{len(linhas)} conta(s) – Total: {moeda(total)} | "
                                   f"Pago: {moeda(pago)} | Saldo: {moeda(saldo)}")


class JanelaNovoPagamento(tk.Toplevel):

    def __init__(self, pai, ao_salvar):
        super().__init__(pai)
        self.title("Novo pagamento")
        self.transient(pai.winfo_toplevel())
        self.grab_set()
        self.svc = PagamentoService()
        self.ao_salvar = ao_salvar

        f = ttk.Frame(self)
        f.pack(padx=12, pady=12)

        ttk.Label(f, text="Conta*").grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.cb_conta = ttk.Combobox(f, width=50, state="readonly")
        self.cb_conta.grid(row=0, column=1, sticky="w")

        self.data = campo(f, "Data (DD/MM/AAAA)*", 1, 15)
        self.data.insert(0, datetime.today().strftime("%d/%m/%Y"))

        ttk.Label(f, text="Forma de pagamento*").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        self.forma = ttk.Combobox(f, values=FORMAS_PAGAMENTO, width=15, state="readonly")
        self.forma.grid(row=2, column=1, sticky="w")

        self.valor_pago = campo(f, "Valor pago pelo paciente (R$)", 3, 15)

        self.tem_convenio = tk.BooleanVar(value=False)

        ttk.Checkbutton(f, text="Pago com convênio", variable=self.tem_convenio,
                        command=self.ajustar_campo_convenio).grid(row=4, column=1, sticky="w", pady=2)
        self.valor_convenio = campo(f, "Valor pago pelo convênio (R$)", 5, 15)
        self.ajustar_campo_convenio()

        ttk.Button(f, text="Salvar", command=self.salvar).grid(row=6, column=1, sticky="w", pady=8)

        self.carregar_contas()

    def ajustar_campo_convenio(self):
        if self.tem_convenio.get():
            self.valor_convenio.config(state="normal")
        else:
            self.valor_convenio.delete(0, "end")
            self.valor_convenio.config(state="disabled")

    def carregar_contas(self):
        contas = executar(self.svc.contas_em_aberto)
        if contas is None:
            contas = []

        self.cb_conta["values"] = [f"{i} - {texto}" for i, texto in contas]

    def salvar(self):
        def chamar_servico():
            return self.svc.registrar(
                id_de(self.cb_conta.get()), self.data.get(), self.forma.get(),
                self.valor_pago.get(), self.tem_convenio.get(), self.valor_convenio.get())

        pagamento_id = executar(chamar_servico)
        if pagamento_id:
            messagebox.showinfo("Pronto", "Pagamento registrado.", parent=self)
            self.ao_salvar()
            self.destroy()


class AbaPagamentos(ttk.Frame):
    TODOS = "Todos"

    def __init__(self, pai):
        super().__init__(pai)
        self.svc = PagamentoService()
        self.pac = PacienteService()
        self.med = MedicoService()


        topo = ttk.Frame(self)
        topo.pack(fill="x", padx=6, pady=6)
        f = ttk.LabelFrame(topo, text="Filtros")
        f.pack(side="left")

        ttk.Button(topo, text="+Novo Pagamento", command=self.abrir_novo_pagamento).pack(side="left", expand=True)

        self.ini = campo(f, "Data inicial (DD/MM/AAAA)", 0, 15)
        self.fim = campo(f, "Data final (DD/MM/AAAA)", 1, 15)

        ttk.Label(f, text="Forma de pagamento").grid(row=2, column=0, sticky="e", padx=4, pady=2)
        self.forma = ttk.Combobox(f, values=[self.TODOS, *FORMAS_PAGAMENTO], width=15, state="readonly")
        self.forma.set(self.TODOS)
        self.forma.grid(row=2, column=1, sticky="w")

        ttk.Label(f, text="Com convênio").grid(row=0, column=2, sticky="e", padx=(16, 4), pady=2)
        self.conv = ttk.Combobox(f, values=[self.TODOS, "Sim", "Não"], width=15, state="readonly")
        self.conv.set(self.TODOS)
        self.conv.grid(row=0, column=3, sticky="w")

        ttk.Label(f, text="Paciente").grid(row=1, column=2, sticky="e", padx=(16, 4), pady=2)
        self.cb_pac = ttk.Combobox(f, width=32, state="readonly")
        self.cb_pac.grid(row=1, column=3, sticky="w")

        ttk.Label(f, text="Médico").grid(row=2, column=2, sticky="e", padx=(16, 4), pady=2)
        self.cb_med = ttk.Combobox(f, width=32, state="readonly")
        self.cb_med.grid(row=2, column=3, sticky="w")

        
        
        bt = ttk.Frame(f)
        bt.grid(row=3, column=1, columnspan=3, sticky="w", pady=4)
        ttk.Button(bt, text="Filtrar", command=self.atualizar).pack(side="left", padx=(0, 4))
        ttk.Button(bt, text="Limpar filtros", command=self.limpar).pack(side="left")

        self.tab = tabela(self, ("ID", "Data", "Paciente", "Médico", "Forma", "Convênio",
                                 "Valor convênio", "Valor pago", "Conta"),
                          (40, 85, 170, 170, 80, 70, 100, 90, 50))
        self.lbl_total = ttk.Label(self, text="", font=("Helvetica", 10, "bold"))
        self.lbl_total.pack(anchor="e", padx=10, pady=(0, 6))
        self.carregar_opcoes()
        self.atualizar()

    def abrir_novo_pagamento(self):
        JanelaNovoPagamento(self, self.atualizar)

    def carregar_opcoes(self):
        def buscar_opcoes():
            return self.pac.opcoes(), self.med.opcoes()

        r = executar(buscar_opcoes)
        if r is None:
            return
        pacientes, medicos = r
        self.cb_pac["values"] = [self.TODOS] + [f"{i} - {n}" for i, n in pacientes]
        self.cb_med["values"] = [self.TODOS] + [f"{i} - {n}" for i, n in medicos]
        self.cb_pac.set(self.TODOS)
        self.cb_med.set(self.TODOS)

    def _id(self, combo):
        t = combo.get()
        return None if not t or t == self.TODOS else id_de(t)

    def limpar(self):
        self.ini.delete(0, "end")
        self.fim.delete(0, "end")
        for c in (self.forma, self.conv, self.cb_pac, self.cb_med):
            c.set(self.TODOS)
        self.atualizar()

    def atualizar(self):
        def valor_do_filtro(combo):
            return "" if combo.get() == self.TODOS else combo.get()

        def buscar_pagamentos():
            return self.svc.listar(
                self.ini.get(), self.fim.get(), valor_do_filtro(self.forma), valor_do_filtro(self.conv),
                self._id(self.cb_pac), self._id(self.cb_med))

        linhas = executar(buscar_pagamentos)
        if linhas is None:
            return
        preencher(self.tab, linhas)
        total = self.svc.total_pago(linhas)
        self.lbl_total.config(
            text=f"{len(linhas)} pagamento(s) – Total pago: R$ {total:,.2f}"
                 .replace(",", "X").replace(".", ",").replace("X", "."))

class TelaLogin(ttk.Frame):
    def __init__(self, pai, on_sucesso):
        super().__init__(pai, style="Verde.TFrame")
        self.on_sucesso = on_sucesso  
        self.auth = ServicoAutenticacao()

        centro = ttk.Frame(self, style="Verde.TFrame")
        centro.pack(expand=True)

        ttk.Label(centro, text="Clínica Médica", font=("Helvetica", 16, "bold"),
                  style="VerdeTitulo.TLabel").pack(pady=(0, 16))

        ttk.Label(centro, text="E-mail", style="Verde.TLabel").pack(anchor="w")
        self.email = ttk.Entry(centro, width=30)
        self.email.pack(pady=(0, 10))
        self.email.focus()

        ttk.Label(centro, text="Senha", style="Verde.TLabel").pack(anchor="w")
        self.senha = ttk.Entry(centro, width=30, show="*")
        self.senha.pack(pady=(0, 16))
        self.senha.bind("<Return>", lambda e: self.entrar())
        tk.Button(centro, text="Entrar", command=self.entrar, bg="#2E7D4F", fg="white",
                  activebackground="#1B5E3F", activeforeground="white", relief="flat",
                  pady=4).pack(fill="x")

    def entrar(self):
        def chamar_servico():
            return self.auth.entrar(self.email.get(), self.senha.get())

        usuario = executar(chamar_servico)
        if usuario:
            self.on_sucesso(usuario)
            
def iniciar():
    raiz = tk.Tk()
    raiz.title("Clínica Médica")
    raiz.geometry("1000x640")

    estilo = ttk.Style()
    estilo.configure("Verde.TFrame", background="#F4FAF6")
    estilo.configure("Verde.TLabel", background="#F4FAF6", foreground="#1F2D26")
    estilo.configure("VerdeTitulo.TLabel", background="#F4FAF6", foreground="#1B5E3F")

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

        abas = [
            ("Início", AbaInicio),
            ("Consultas", AbaConsultas),
            ("Pacientes", AbaPacientes),
            ("Médicos", AbaMedicos),
            ("Contas", AbaContas),
            ("Pagamentos", AbaPagamentos),
        ]
        permitidas = PERMISSOES.get(usuario["perfil"], [])
        for nome, classe in abas:
            if nome in permitidas:
                nb.add(classe(nb), text=nome)

        def ao_trocar_de_aba(_evento):
            aba = nb.nametowidget(nb.select())
            if hasattr(aba, "ao_exibir"):
                aba.ao_exibir()
        nb.bind("<<NotebookTabChanged>>", ao_trocar_de_aba)


    login = TelaLogin(raiz, abrir_sistema)
    login.pack(fill="both", expand=True)


    raiz.mainloop()