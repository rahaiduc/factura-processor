from dataclasses import dataclass, field


@dataclass
class Attachment:
    filename: str
    data: bytes


@dataclass
class Email:
    id: str
    subject: str
    attachments: list[Attachment] = field(default_factory=list)
