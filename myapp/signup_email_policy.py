"""
Registro por correo: política complementaria cuando no hay envío SMTP.

- No se puede demostrar que el usuario *posee* un inbox sin mandarle un mensaje
  (verificación «mandatory» de django-allauth + templates de correo en templates/account/).

- Con ACCOUNT_EMAIL_VERIFICATION='none', al menos se rechazan dominios típicos de
  correo temporal (lista abajo). Ajustá la lista o poné BLOCK_DISPOSABLE_SIGNUP_EMAILS=False en settings.

Para volver a verificación por enlace cuando tengas SMTP/API operativos:
  1) En mysite/settings (o variable de entorno) ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
  2) Configurá EMAIL_* o SENDGRID_API_KEY según mysite/settings.py
  3) Probá signup y el enlace de /accounts/confirm-email/
"""

# Dominios comunes de servicios de correo temporal / desechable (ampliar según necesidad).
DISPOSABLE_EMAIL_DOMAINS = frozenset({
    'mailinator.com',
    'guerrillamail.com',
    'guerrillamail.org',
    'sharklasers.com',
    'yopmail.com',
    'tempmail.com',
    'temp-mail.org',
    '10minutemail.com',
    'trashmail.com',
    'dispostable.com',
    'maildrop.cc',
    'getnada.com',
    'fakeinbox.com',
    'throwaway.email',
})
