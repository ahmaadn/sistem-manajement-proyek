from fastapi_mail import FastMail, MessageSchema

from app.core.config import settings


class EmailService:
    def __init__(self):
        self.conf = settings.mail_config
        self.mailer = FastMail(self.conf)

    async def send_email(self, subject: str, email_to: str, body: str):
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            body=body,
            subtype="html",
        )
        await self.mailer.send_message(message)
