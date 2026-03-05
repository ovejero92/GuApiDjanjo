# 🗓️ Gestor de Turnos Online - TurnosOk

[![Figma](https://img.shields.io/badge/Design-Figma-F24E1E?style=flat&logo=figma&logoColor=white)](https://www.figma.com/design/6mCX5mWYZjc4KhuEdvV2XO/TurnosOk?node-id=1004-76&t=q68bTDDbGn0VlZy3-1)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-Framework-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Status](https://img.shields.io/badge/Status-En_Producción-brightgreen)](https://turnosok.com/)

## 📝 Descripción

**TurnosOk** es una plataforma web integral diseñada para la gestión de turnos online. Es una solución versátil para negocios de servicios (peluquerías, centros de estética, consultas médicas, etc.) que permite automatizar el agendamiento tanto para el profesional como para el cliente final.

🚀 **Ver en vivo:** [turonsok.com](https://turnosok.com/)

---

## 🎨 Diseño UI/UX (Figma)

Para este proyecto, el diseño fue una prioridad antes de pasar al código. Se utilizó **Figma** para definir la arquitectura de información, el flujo de usuario y los componentes visuales, asegurando una experiencia intuitiva.

* **Prototipo Interactivo:** [Acceder al Proyecto en Figma](https://www.figma.com/design/6mCX5mWYZjc4KhuEdvV2XO/TurnosOk?node-id=1004-76&t=q68bTDDbGn0VlZy3-1)
* **Enfoque:** Diseño *mobile-first*, paleta de colores profesional y componentes reutilizables (Botones, Inputs, Cards).
* **User Flow:** Se diseñaron flujos diferenciados para el Administrador (Dashboard) y el Cliente (Reserva rápida).

> **Nota para reclutadores:** El archivo de Figma refleja el uso de Auto Layout, estilos globales y una estructura de capas organizada, alineada con las mejores prácticas de desarrollo frontend.

---

## ✨ Características Principales

La plataforma ofrece una experiencia rica y diferenciada para dos tipos de usuarios:

### 👤 Para Propietarios de Negocios (Profesionales)
* **Gestión de Servicios:** Control total sobre precios, duraciones y descripciones.
* **Gestión de Horarios:** Configuración de disponibilidad, feriados y excepciones.
* **Panel de Control:** Métricas clave y gestión centralizada de citas.
* **Suscripción Premium:** Integración de pagos para funcionalidades avanzadas.

### 👥 Para Clientes (Usuarios Finales)
* **Reserva de Turnos:** Selección de horarios en tiempo real con interfaz intuitiva.
* **Mis Turnos:** Historial y gestión (cancelación/reprogramación) de citas.
* **Reseñas:** Sistema de valoración para feedback de servicios.

---

## 🛠️ Tecnologías Utilizadas

### Backend & Database
* **Python / Django:** Core del negocio y lógica de servidor.
* **Django REST Framework:** Implementación de APIs robustas.
* **PostgreSQL:** Base de datos relacional para producción.
* **MercadoPago SDK:** Pasarela de pagos integrada.

### Frontend
* **HTML5 / CSS3 / JavaScript:** Interfaz dinámica y responsiva.
* **Figma:** Herramienta principal de prototipado y diseño de interfaz.

### DevOps & Cloud
* **Render:** Hosting y despliegue continuo.
* **AWS S3 / Boto3:** Almacenamiento de archivos y medios.
* **WhiteNoise:** Optimización de archivos estáticos.

---

## 🚀 Instalación y Uso Local

1.  **Clonar el Repositorio:**
    ```bash
    git clone [https://github.com/ovejero92/GuApiDjanjo.git](https://github.com/ovejero92/GuApiDjanjo.git)
    cd GuApiDjanjo
    ```

2.  **Entorno Virtual:**
    ```bash
    python -m venv venv
    # Activar (Windows)
    .\venv\Scripts\activate
    # Activar (macOS/Linux)
    source venv/bin/activate
    ```

3.  **Dependencias y Migraciones:**
    ```bash
    pip install -r requirements.txt
    python manage.py migrate
    ```

4.  **Correr Servidor:**
    ```bash
    python manage.py runserver
    ```

---

## 📈 Mejoras Futuras
* 🔔 Notificaciones vía WhatsApp/Email en tiempo real.
* 📅 Sincronización bidireccional con Google Calendar.
* 📊 Dashboard de analíticas avanzadas con gráficos.

---

## 📩 Contacto

**Gustavo Ovejero** 📧 [ovejero.gustavo92@gmail.com](mailto:ovejero.gustavo92@gmail.com)  
🔗 [LinkedIn](https://www.linkedin.com/in/gustavo-ovejero/) | [GitHub](https://github.com/ovejero92)

---
*Este proyecto fue desarrollado con un enfoque en la escalabilidad y la experiencia de usuario.*