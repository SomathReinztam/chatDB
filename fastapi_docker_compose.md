Muy buena pregunta 👌 — y sí, **apilar todos los endpoints en `main.py` no es buena práctica** si el proyecto va a crecer.

Tu estructura ya está bastante bien pensada, solo necesitas aplicar una separación típica en FastAPI: **routers por dominio**.

---

# 🎯 Problema actual

Ahora tienes:

```
src/api/main.py
```

Y ahí defines:

* `/newuser`
* `/runchat`
* probablemente más en el futuro

Eso escala mal porque:

* main.py se vuelve enorme
* Mezclas responsabilidades
* Es difícil testear
* Es difícil encontrar cosas

---

# ✅ Organización recomendada (Clean FastAPI structure)

Te propongo esta estructura:

```
src/
│
├── api/
│   ├── main.py
│   └── v1/
│       ├── routers/
│       │   ├── users.py
│       │   ├── chat.py
│       │   └── health.py
│       │
│       └── schemas/
│           ├── user.py
│           └── chat.py
│
├── services/
│   ├── chat_service.py
│   └── user_service.py
```

---

# 🔥 Paso 1 — Separar Routers

## 📁 src/api/v1/routers/users.py

```python
from fastapi import APIRouter
from src.api.v1.schemas.user import PostNewUser, MessageResponse
from src.database.crud.crud import CrudHelper
from src.utils import settings

router = APIRouter(prefix="/users", tags=["Users"])

crud_helper = CrudHelper(
    db_host=settings.DB_HOST,
    db_pass=settings.DB_PASS,
    db_user=settings.DB_USER,
    db_name=settings.DB_NAME,
    db_port=settings.DB_PORT,
)

@router.post("/", response_model=MessageResponse)
async def create_user(body: PostNewUser):
    crud_helper.post_new_user(
        name=body.name,
        db_credentials=body.db_credentials
    )
    return MessageResponse(message="Usuario creado exitosamente.")
```

---

## 📁 src/api/v1/routers/chat.py

```python
from fastapi import APIRouter
from src.api.v1.schemas.chat import RunChat, RunChatResponse
from src.database.crud.run_chat import run_chat

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/run", response_model=RunChatResponse)
async def run_chat_api(body: RunChat):
    return run_chat(
        user_id=body.user_id,
        chat_id=body.chat_id,
        human_message=body.human_message
    )
```

---

# 🔥 Paso 2 — Separar Schemas

## 📁 src/api/v1/schemas/chat.py

Aquí van todos los modelos Pydantic.

## 📁 src/api/v1/schemas/user.py

Aquí los modelos de usuario.

Esto mantiene separado:

* API contracts (schemas)
* Lógica de negocio
* Base de datos

---

# 🔥 Paso 3 — main.py minimalista

## 📁 src/api/main.py

```python
from fastapi import FastAPI
from src.api.v1.routers import users, chat

app = FastAPI(title="ChatPostgres API")

app.include_router(users.router)
app.include_router(chat.router)
```

---

# 🧠 Beneficios

✔ Separación clara por dominio
✔ Escalable
✔ Fácil de testear
✔ Documentación Swagger organizada por tags
✔ Preparado para versionado (`/v1`, `/v2`)

---

# 🚀 Extra Pro (muy recomendado)

Si tu proyecto va a crecer:

```
src/
├── core/            # config, settings, logging
├── api/
├── services/        # lógica de negocio
├── repositories/    # acceso a BD
```

Entonces:

* `api` → solo HTTP
* `services` → lógica
* `repositories` → base de datos

Eso es arquitectura limpia real.

---

# 📌 Para tu caso concreto

Con lo que ya tienes, lo mínimo que deberías hacer es:

```
src/api/
├── main.py
├── routers/
│   ├── users.py
│   └── chat.py
└── schemas/
    ├── user.py
    └── chat.py
```

Y dejar `main.py` solo como ensamblador.

---

Si quieres, puedo proponerte una estructura aún más alineada con proyectos de ML + LLM + RAG como el tuyo (porque tu proyecto no es una API simple, es un sistema con agentes y herramientas).


---

.

.

.

.

.

.

.

.

---

Perfecto 👌 esto es exactamente para lo que sirve el archivo `.env` en Docker Compose.

Docker Compose **sí puede interpolar variables del `.env` directamente en el YAML** usando `${VARIABLE}`.

---

# ✅ Paso 1 — Crea tu `.env` en la raíz del proyecto

En el mismo nivel donde está `docker-compose.yaml`:

```
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=chatpostgres
```

---

# ✅ Paso 2 — Usa las variables en `docker-compose.yaml`

```yaml
services:
  postgres-db:
    image: pgvector/pgvector:pg16
    container_name: chat-postgres-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT}:5432"
```

---

# 🔥 ¿Qué está pasando aquí?

```yaml
"${POSTGRES_PORT}:5432"
```

Significa:

```
puerto_maquina:puerto_contenedor
```

Entonces si en `.env` tienes:

```
POSTGRES_PORT=5433
```

Tu contenedor expondrá:

```
localhost:5433 -> contenedor:5432
```

---

# ⚠️ Importante

Docker Compose:

* Carga automáticamente el archivo `.env`
* Debe estar en el mismo directorio que `docker-compose.yaml`
* No necesitas declararlo explícitamente

---

# 🧠 Si también quieres parametrizar el puerto interno

Podrías hacer:

`.env`

```
POSTGRES_PORT=5433
POSTGRES_CONTAINER_PORT=5432
```

`docker-compose.yaml`

```yaml
ports:
  - "${POSTGRES_PORT}:${POSTGRES_CONTAINER_PORT}"
```

---

# 🚀 Extra útil

Si quieres verificar qué valores está leyendo docker:

```bash
docker compose config
```

Eso te muestra el YAML final ya interpolado.

---

# 🔥 Consejo importante para tu proyecto

Como ya usas `settings.py`, es buena práctica que:

* `.env` sea compartido por:

  * Docker
  * FastAPI (usando `python-dotenv` o `pydantic-settings`)

Así no duplicas configuración.

---

Si quieres, puedo ayudarte a dejar:

* `.env`
* docker-compose
* settings.py

bien integrados y limpios para producción.
