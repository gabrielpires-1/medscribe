from app.extraction.schemas import (
    ConsultationDocuments,
    ExamOrders,
    Prescription,
    SoapNote,
)


def fake_consultation_documents() -> ConsultationDocuments:
    return ConsultationDocuments(
        medical_record=SoapNote(
            subjective="lorem-ipsum-subjetivo",
            objective="",
            assessment="",
            plan="lorem-ipsum-plano",
        ),
        prescription=Prescription(medications=[]),
        exam_orders=ExamOrders(exams=[]),
    )
