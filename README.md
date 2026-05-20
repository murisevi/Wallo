# Wallo

Wallo es una aplicacion web de finanzas personales desarrollada como TFG. Permite
registrarse, conectar cuentas bancarias mediante PSD2/Open Banking con Enable
Banking, sincronizar saldos y transacciones, categorizar movimientos, gestionar
presupuestos, detectar cobros recurrentes, consultar informes y reservar dinero
virtualmente para objetivos de ahorro.

## Stack

| Capa | Tecnologia |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, TanStack Query |
| Backend | FastAPI, Python 3.12, SQLAlchemy async, Pydantic v2, Alembic |
| Base de datos | PostgreSQL 16 |
| Cache | Redis 7, opcional pero incluido en Docker |
| Open Banking | Enable Banking |
| Desarrollo/despliegue local | Docker Compose, nginx, pgAdmin |

## Requisitos

Para ejecutar todo con Docker:

- Docker Desktop o Docker Engine con Docker Compose.
- Una aplicacion sandbox de Enable Banking si quieres probar la conexion bancaria real.

Para desarrollo sin Docker tambien necesitas:

- Python 3.12 o superior.
- Node.js 20 o superior.
- npm.

## Configuracion inicial

Clona el repositorio y crea tu archivo de entorno:

```bash
git clone https://github.com/murisevi/Wallo.git
cd Wallo
cp .env.example .env
```

En Windows PowerShell, si no tienes `cp` disponible:

```powershell
Copy-Item .env.example .env
```

Edita `.env` y revisa estos valores:

```env
JWT_SECRET_KEY=pon-aqui-un-secreto-largo-y-aleatorio
ENABLE_BANKING_APP_ID=tu-application-id
ENABLE_BANKING_PRIVATE_KEY_PATH=keys/private.pem
ENABLE_BANKING_ENVIRONMENT=sandbox
ENABLE_BANKING_REDIRECT_URL=https://localhost:3000/banking/callback
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
CORS_ORIGINS=http://localhost:3000,https://localhost:3000
```

La clave privada `.pem` de Enable Banking debe guardarse en:

```text
Backend/keys/private.pem
```

La ruta del `.env` es relativa al backend, por eso el valor recomendado es
`keys/private.pem`. No subas nunca esa clave al repositorio.

## Configurar Enable Banking

1. Entra en el panel de Enable Banking y crea una aplicacion en modo sandbox.
2. Copia el Application ID en `ENABLE_BANKING_APP_ID`.
3. Descarga la clave privada `.pem` y guardala como `Backend/keys/private.pem`.
4. Registra esta redirect URL para la ejecucion con Docker:

```text
https://localhost:3000/banking/callback
```

El contenedor de nginx usa HTTPS con un certificado autofirmado para localhost.
El navegador mostrara un aviso de seguridad la primera vez; aceptalo solo en
desarrollo local.

## Ejecucion recomendada con Docker

En el primer arranque, levanta primero la infraestructura, aplica migraciones y
despues arranca la aplicacion completa:

```bash
docker compose build
docker compose up -d db redis
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

En arranques posteriores normalmente basta con:

```bash
docker compose up -d
```

La aplicacion quedara disponible en:

- Frontend: https://localhost:3000
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- pgAdmin: http://localhost:5050

Credenciales por defecto de pgAdmin:

```text
Email: admin@wallo.com
Password: admin
```

Para ver logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Para parar los servicios sin borrar datos:

```bash
docker compose down
```

Para parar y borrar tambien el volumen de PostgreSQL:

```bash
docker compose down -v
```

## Primer uso

1. Abre https://localhost:3000.
2. Acepta el certificado local si el navegador lo solicita.
3. Registra un usuario.
4. Inicia sesion.
5. Ve a la opcion de conectar banco.
6. Selecciona un banco sandbox, normalmente BBVA o Mock ASPSP segun tu cuenta de Enable Banking.
7. Completa el flujo de autorizacion.
8. Al volver a Wallo, el backend sincronizara cuentas, saldos y transacciones.

## Desarrollo local sin ejecutar toda la app en Docker

Puedes usar Docker solo para PostgreSQL y Redis, y ejecutar backend/frontend en
tu maquina.

### 1. Levantar PostgreSQL y Redis

```bash
docker compose up -d db redis
```

### 2. Backend

Desde otra terminal:

```bash
cd Backend
python -m venv .venv
```

Activar entorno virtual:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov ruff
```

Aplicar migraciones y arrancar FastAPI:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

Desde otra terminal:

```bash
cd frontend
npm install
npm run dev
```

El frontend local de Next.js escucha en:

```text
http://localhost:3001
```

Si usas este modo sin nginx, ajusta `.env` para que el backend acepte el origen
del frontend y para que Enable Banking vuelva al puerto correcto:

```env
ENABLE_BANKING_REDIRECT_URL=http://localhost:3001/banking/callback
CORS_ORIGINS=http://localhost:3001,http://localhost:3000,https://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Tambien debes registrar `http://localhost:3001/banking/callback` como redirect
URL en Enable Banking si vas a probar la conexion bancaria en este modo.

## Comandos utiles

Backend:

```bash
cd Backend
pytest tests/ -v --cov=app
ruff check app/ tests/
ruff format app/ tests/
alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Docker:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose run --rm backend alembic current
docker compose run --rm backend alembic upgrade head
```

## Variables de entorno principales

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | Conexion SQLAlchemy async a PostgreSQL. Docker la sobreescribe para usar `db`. |
| `REDIS_URL` | Conexion a Redis. Docker la sobreescribe para usar `redis`. |
| `JWT_SECRET_KEY` | Secreto para firmar tokens JWT. Cambialo siempre fuera de demo. |
| `ENABLE_BANKING_APP_ID` | ID de la aplicacion en Enable Banking. |
| `ENABLE_BANKING_PRIVATE_KEY_PATH` | Ruta de la clave `.pem`, relativa a `Backend/`. |
| `ENABLE_BANKING_ENVIRONMENT` | Normalmente `sandbox` en desarrollo. |
| `ENABLE_BANKING_REDIRECT_URL` | URL a la que Enable Banking devuelve el `code`. |
| `NEXT_PUBLIC_API_URL` | URL publica del backend que usa el frontend. |
| `CORS_ORIGINS` | Origenes permitidos por FastAPI, separados por comas. |

## Solucion de problemas

Si el backend arranca pero no conecta con Enable Banking:

- Comprueba que `ENABLE_BANKING_APP_ID` existe en `.env`.
- Comprueba que `Backend/keys/private.pem` existe.
- Comprueba que `ENABLE_BANKING_PRIVATE_KEY_PATH=keys/private.pem`.
- Revisa `docker compose logs -f backend`.

Si el flujo bancario vuelve con error:

- Confirma que la redirect URL registrada en Enable Banking coincide exactamente
  con `ENABLE_BANKING_REDIRECT_URL`.
- En Docker usa `https://localhost:3000/banking/callback`.
- En desarrollo sin nginx usa `http://localhost:3001/banking/callback`.

Si el frontend no puede llamar al backend:

- Comprueba `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.
- Comprueba que `CORS_ORIGINS` incluye el origen desde el que abres el frontend.
- Revisa la consola del navegador y los logs del backend.

Si la base de datos esta vacia o faltan tablas:

```bash
docker compose run --rm backend alembic upgrade head
```

Si quieres reiniciar completamente la base de datos local:

```bash
docker compose down -v
docker compose build
docker compose up -d db redis
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

## Seguridad

No subas al repositorio:

- `.env`
- claves `.pem`
- tokens
- credenciales bancarias
- dumps de base de datos con datos reales

El archivo `.gitignore` ya ignora los archivos sensibles y los documentos locales
de planificacion del proyecto.

## Licencia

Proyecto desarrollado como Trabajo de Fin de Grado. No incluye una licencia de
uso externo por defecto.
