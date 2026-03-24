from dataclasses import dataclass

@dataclass
class LOASchema:
    authorizer: str
    authorized_person: str
    scope: str
    date: str

@dataclass
class NoticeSchema:
    recipient: str
    subject: str
    notice_date: str

@dataclass
class BusinessDocSchema:
    company: str
    amount: str
    date: str