"""Camada de negócio: classes de domínio."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass
class Paciente:
    nome: str
    cpf: str
    data_nasc: Optional[date] = None
    rg: str = ""
    sexo: str = ""
    endereco: str = ""
    email: str = ""
    telefones: List[str] = field(default_factory=list)


@dataclass
class Medico:
    nome: str
    crm: str
    percentual: float
    telefone: str = ""
    especialidades: List[int] = field(default_factory=list)
    horarios: List[int] = field(default_factory=list)


@dataclass
class Consulta:
    id_paciente: int
    id_medico: int
    id_sala: int
    data_hora: datetime
    valor: float
    status: str = "AGENDADA"
