<div align="center">
  <img src="https://raw.githubusercontent.com/creepiman854/balapedia/main/frontend/public/images/balapedia_logo.png" alt="Balapedia Logo" width="300"/>

  # Balapedia

  **El Companion App y Tracker de Progresión definitivo para Balatro.** *Sincronización en tiempo real, gestión de colección y una experiencia Pixel-Perfect.*

  [![Vue.js](https://img.shields.io/badge/Vue%203-35495E?style=for-the-badge&logo=vue.js&logoColor=4FC08D)](#)
  [![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](#)
  [![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](#)
  [![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](#)
  [![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](#)
</div>

---

## 🃏 ¿Qué es Balapedia?

**Balapedia** es una aplicación web integral diseñada para los jugadores de *Balatro*. Actúa como una enciclopedia interactiva y un rastreador de progresión (Tracker) que permite a los usuarios gestionar su colección completa de Jokers, Tarots, Planetas, Espectrales, Barajas y Vouchers.

El proyecto nace con el objetivo de ofrecer una herramienta visualmente inmersiva —respetando la estética retro, CRT y pixel-art del juego original— combinada con una arquitectura backend robusta capaz de automatizar la extracción de datos y sincronizar el progreso del jugador directamente con Steam.

## ✨ Características Principales

* 🔄 **Sincronización con Steam:** Conecta tu cuenta de Steam de forma segura (OpenID) y sincroniza automáticamente tus logros y tu colección del juego en un solo clic.
* ✍️ **Tracking Manual Dual:** ¿Juegas en consola (Switch, PS5, Xbox)? No hay problema. Balapedia permite llevar un registro manual paralelo al de Steam para que ningún jugador se quede atrás.
* 🏆 **Motor de Cascadas de Desbloqueo:** Un sistema inteligente que detecta los logros obtenidos y propaga sus efectos de forma automática. Esto no se limita a gestionar los hitos globales (*Completionist, Completionist+ y Completionist++*) que aplican *Gold Stickers* masivamente, sino que sincroniza de forma inmediata cualquier carta o elemento del juego que comparta el mismo método de desbloqueo.
* 🖥️ **Estética Inmersiva:** Interfaz construida con shaders WebGL de fondo, filtros CRT interactivos, fuentes pixel-art (`m6x11plus`) y una capa de overlays decorativos sin sacrificar el rendimiento (*0% lag en scroll*).
* 🕷️ **Scraping Automatizado:** Datos siempre actualizados. El backend se alimenta directamente de la MediaWiki oficial de Balatro y de la Steam Web API mediante un comando de orquestación personalizado (`flask seed-db`).
* 📱 **Diseño Responsive:** Experiencia fluida adaptada a PC, Tablets y Móviles, incluyendo un *drawer* lateral personalizado y cabeceras dinámicas.

---

## 🛠️ Stack Tecnológico y Arquitectura

El proyecto está diseñado bajo una arquitectura desacoplada (Frontend/Backend) desplegada en entornos separados para optimizar el rendimiento y los costes operativos.

### Frontend (Desplegado en Vercel)
* **Framework:** Vue 3 (Composition API) + Vite.
* **Estado & Enrutamiento:** Pinia & Vue Router.
* **Estilos:** SCSS modular con variables globales y mixins personalizados.
* **Efectos:** Animaciones CSS avanzadas y *shaders* WebGL (Background + Sparkles).

### Backend (Desplegado en Render)
* **Core:** Python 3 + Flask (Application Factory Pattern).
* **Base de Datos & ORM:** MySQL (Clever Cloud) + SQLAlchemy + Flask-Migrate.
* **Extracción de Datos (Scraping):** `mwparserfromhell` (Action API MediaWiki) y llamadas HTTP a la Steam Web API.
* **Servidor de Producción:** Gunicorn configurado para bajo consumo de memoria (1 worker, timeout optimizado).

### Seguridad y Autenticación
* **Firebase Auth:** Gestión de sesiones, JWT y correos electrónicos.
* **Integración OAuth:** Sistema Steam OpenID adaptado a Proxies Inversos (`ProxyFix`) para retornos HTTPS seguros.
* **CORS Policies:** Configuración estricta inter-dominios (`Flask-CORS`).

---

## 🚀 Despliegue y Optimizaciones N+1

El desarrollo de la aplicación superó importantes desafíos de infraestructura y rendimiento, logrando un despliegue de alta disponibilidad:

* **Mitigación de Consultas N+1:** El sistema de resolución masiva de logros (como *Completionist++*, que afecta a cientos de cartas simultáneas) procesa toda la colección en memoria RAM (diccionarios pre-cargados) desactivando el autoflush del ORM. Esto redujo el tiempo de respuesta de **>60 segundos a <400 ms**.
* **Gestión de Memoria Segura:** En entornos con recursos limitados (512MB RAM en Render), se configuraron los workers y se implementaron pools de base de datos elásticos (`pool_pre_ping`, `pool_recycle`) para evitar cuelgues (SIGKILL) y desconexiones silenciosas.
* **Idempotencia Transaccional:** El sistema de sembrado de datos (`seed-db`) es atómico por ítem. Si la API externa falla en una carta, el resto del catálogo se sigue actualizando limpiamente.

---

## 💻 Instalación y Desarrollo Local

### Requisitos previos
* Node.js (v18+)
* Python (v3.10+)
* MySQL local o remoto

### Configuración del Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Configurar variables de entorno (copiar .env.example a .env)
# Inicializar la base de datos y poblar los datos oficiales
flask db upgrade
flask seed-db --type=all

# Iniciar servidor local (http://localhost:8080)
flask run --port=8080
```
## Configuración del Frontend
```bash
cd frontend
npm install

# Configurar variables de entorno (.env)
# Iniciar servidor de desarrollo
npm run dev
```
---
## 📝 Autor
Adrián - Diseño, Arquitectura y Desarrollo Full-Stack. Desarrollado como Proyecto Final de Grado (TFG) para el ciclo de Desarrollo de Aplicaciones Web (DAW).
