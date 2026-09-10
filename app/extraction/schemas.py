from pydantic import BaseModel


class SoapNote(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


class Medication(BaseModel):
    name: str
    dosage: str
    route: str
    frequency: str
    duration: str
    instructions: str


class Prescription(BaseModel):
    medications: list[Medication]


class ExamOrder(BaseModel):
    name: str
    indication: str
    instructions: str


class ExamOrders(BaseModel):
    exams: list[ExamOrder]


class ConsultationDocuments(BaseModel):
    medical_record: SoapNote
    prescription: Prescription
    exam_orders: ExamOrders
