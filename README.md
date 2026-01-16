# Gestor de Turnos Online

## Descripción

Este proyecto es una plataforma web completa diseñada para la gestión de turnos online, atendiendo a una amplia variedad de servicios como peluquerías, peluquerías caninas, consultas, y cualquier otro negocio que requiera un sistema de agendamiento. La aplicación está pensada para ser utilizada tanto por propietarios de negocios (profesionales) como por sus clientes, ofreciendo una experiencia dual e integral. Actualmente, la aplicación se encuentra en producción en Render.

## Características

La plataforma ofrece una experiencia rica y diferenciada para dos tipos de usuarios:

### Para Propietarios de Negocios (Profesionales)

*   **Gestión de Servicios:** Creación, edición y eliminación de servicios ofrecidos, incluyendo detalles como duración, precios, y descripción.
*   **Gestión de Horarios:** Configuración de disponibilidad laboral, días no laborables y excepciones para cada servicio o profesional.
*   **Gestión de Turnos:** Visualización de todos los turnos agendados, confirmación, cancelación y modificación.
*   **Panel de Control Personalizado:** Vista administrativa para gestionar todos los aspectos del negocio, con métricas y herramientas de análisis.
*   **Perfiles Personalizables:** Posibilidad de modificar la apariencia y la información de sus páginas de servicio.
*   **Suscripción Premium:** Acceso a funcionalidades avanzadas mediante un modelo de suscripción mensual.

### Para Clientes (Usuarios Finales)

*   **Exploración de Servicios:** Navegación por un catálogo de servicios disponibles.
*   **Reserva de Turnos:** Selección de servicios y horarios disponibles para agendar citas de forma sencilla.
*   **Gestión de Mis Turnos:** Visualización y cancelación de turnos agendados.
*   **Perfiles de Usuario:** Creación y gestión de perfiles para un proceso de reserva más ágil.
*   **Calificaciones y Reseñas:** Posibilidad de dejar valoraciones y comentarios sobre los servicios recibidos.



## Tecnologías Utilizadas

El proyecto está construido utilizando un stack robusto y moderno:

*   **Backend:**
    *   Python 3
    *   Django (Framework Web)
    *   Django REST Framework (Para la API)
    *   `psycopg2-binary` (Adaptador PostgreSQL)
    *   `gunicorn` (Servidor WSGI)
    *   `django-allauth` (Autenticación)
    *   `mercadopago` (Integración de pagos)
    *   `boto3` y `django-storages` (Gestión de archivos en S3/Cloud Storage)
    *   `whitenoise` (Servicio de archivos estáticos)
*   **Frontend:**
    *   HTML5
    *   CSS3 (con `main.css` y posible uso de algún framework o preprocesador)
    *   JavaScript
*   **Base de Datos:**
    *   PostgreSQL (recomendado para producción, aunque se usa `db.sqlite3` para desarrollo por defecto).
*   **Despliegue:**
    *   Render (Plataforma de despliegue en la nube)


## Instalación

Sigue estos pasos para configurar y ejecutar el proyecto localmente:

1.  **Clonar el Repositorio:**

    ```bash
    git clone https://github.com/tu-usuario/nombre-del-repo.git
    cd nombre-del-repo
    ```

    *(Recuerda reemplazar `https://github.com/tu-usuario/nombre-del-repo.git` y `nombre-del-repo` con los datos reales de tu repositorio.)*

2.  **Crear y Activar un Entorno Virtual:**

    ```bash
    python -m venv venv
    # En Windows
    .\venv\Scripts\activate
    # En macOS/Linux
    source venv/bin/activate
    ```

3.  **Instalar Dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno:**

    Crea un archivo `.env` en la raíz del proyecto y añade tus variables de entorno. Puedes usar el archivo `mysite/settings.py` como referencia.
    Ejemplo básico:
    ```
    SECRET_KEY=tu_clave_secreta_aqui
    DEBUG=True
    DATABASE_URL=sqlite:///db.sqlite3
    # Otras variables como las de MercadoPago, AWS S3, etc.
    ```

5.  **Ejecutar Migraciones:**

    ```bash
    python manage.py migrate
    ```

6.  **Crear un Superusuario (Opcional, para acceder al panel de administración de Django):**

    ```bash
    python manage.py createsuperuser
    ```

7.  **Iniciar el Servidor de Desarrollo:**

    ```bash
    python manage.py runserver
    ```

    Ahora puedes acceder a la aplicación en tu navegador en `http://127.0.0.1:8000/`.


## Despliegue

La aplicación está desplegada en producción utilizando [Render](https://turnosok.com/). Render es una plataforma de nube que facilita el despliegue continuo de aplicaciones web.

### Pasos Generales para el Despliegue en Render:

1.  **Conectar Repositorio:** Vincula tu repositorio de GitHub/GitLab a Render.
2.  **Configurar Servicio Web:** Crea un nuevo servicio web y configura los comandos de build y start. Para una aplicación Django con Gunicorn y Whitenoise, podría ser similar a:
    *   **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --noinput`
    *   **Start Command:** `gunicorn mysite.wsgi:application --bind 0.0.0.0:$PORT`
3.  **Configurar Base de Datos:** Conecta una base de datos PostgreSQL gestionada por Render (o externa).
4.  **Variables de Entorno:** Configura todas las variables de entorno necesarias (SECRET_KEY, DATABASE_URL, AWS_ACCESS_KEY_ID, etc.) en el panel de Render.
5.  **Migraciones en Producción:** Asegúrate de que las migraciones se ejecuten en cada despliegue. Esto se puede hacer con un `health check path` o un `post-deploy command` en Render, por ejemplo: `python manage.py migrate --noinput`.

Para más detalles, consulta la documentación oficial de [Render](https://render.com/docs/deploy-django).


## Mejoras Futuras

Algunas de las mejoras y funcionalidades que se podrían implementar en el futuro incluyen:

*   **Notificaciones en Tiempo Real:** Implementación de notificaciones vía webhooks o websockets para eventos como nuevas reservas, cancelaciones o recordatorios.
*   **Integración con Calendarios Externos:** Sincronización con calendarios de Google Calendar u Outlook para una mejor gestión de la disponibilidad.
*   **Módulo de Reportes Avanzados:** Generación de reportes personalizables y análisis de datos más profundos para los profesionales.
*   **Optimización de Rendimiento:** Mejoras en la carga de la página y la respuesta de la API para una experiencia de usuario más fluida.
*   **Aplicación Móvil:** Desarrollo de aplicaciones nativas o híbridas para iOS y Android.

## Pruebas (Testing)

El proyecto incluye un conjunto de pruebas unitarias y de integración para asegurar la calidad y el correcto funcionamiento de la aplicación. Se utilizan las herramientas de testing de Django.

Para ejecutar las pruebas, utiliza el siguiente comando:

```bash
python manage.py test
```

## Uso

Una vez que la aplicación esté en funcionamiento (ya sea localmente o desplegada), los usuarios pueden:

1.  **Registrarse/Iniciar Sesión:** Acceder a la plataforma creando una cuenta o utilizando credenciales existentes.
2.  **Explorar Servicios:** Navegar por los diferentes servicios ofrecidos por los profesionales.
3.  **Reservar un Turno:** Seleccionar un servicio, elegir una fecha y hora disponible, y confirmar la reserva.
4.  **Gestionar Perfiles (Profesionales):** Acceder al dashboard para configurar servicios, horarios y gestionar turnos.
5.  **Ver Mis Turnos (Clientes):** Consultar los turnos agendados y, si es permitido, cancelarlos.

## Contribución

¡Las contribuciones son bienvenidas! Si deseas contribuir a este proyecto, por favor sigue estos pasos:

1.  Haz un *fork* del repositorio.
2.  Crea una nueva rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`).
3.  Realiza tus cambios y asegúrate de que el código pase los tests.
4.  Haz *commit* de tus cambios (`git commit -m 'feat: Añade nueva funcionalidad'`).
5.  Haz *push* a tu rama (`git push origin feature/nueva-funcionalidad`).
6.  Abre un *Pull Request* explicando tus cambios.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` (si existe) para más detalles.

## Contacto

Si tienes alguna pregunta o sugerencia, no dudes en contactarme:

*   **Tu Nombre:** [Gustavo Ovejero]
*   **Email:** [ovejero.gustavo92@gmail.com]
*   **LinkedIn:** [https://www.linkedin.com/in/gustavo-ovejero/]
*   **GitHub:** [https://github.com/gustavoovejero]

