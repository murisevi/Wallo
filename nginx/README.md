# Nginx — SSL Termination para desarrollo local

## Por qué existe este servicio

Enable Banking en modo **producción** exige que la redirect URL use **HTTPS**.
El frontend Next.js corre en HTTP puro dentro de Docker, por lo que se añadió
Nginx como reverse proxy que termina TLS antes de reenviar el tráfico internamente.

```
Browser → https://localhost:3000 → Nginx (TLS) → http://frontend:3001 (Next.js)
```

## Certificado

Se genera un certificado **auto-firmado para localhost** en tiempo de build
(`nginx/Dockerfile` usa `openssl`). Es intencional e inseguro — solo para desarrollo.

La primera vez que se accede a `https://localhost:3000` el navegador muestra
una advertencia. En Chrome: **Avanzado → Continuar a localhost (no seguro)**.

## Puertos

| Servicio  | Puerto interno | Puerto externo | Protocolo |
|-----------|---------------|----------------|-----------|
| frontend  | 3001          | —              | HTTP      |
| nginx     | 3000          | 3000           | HTTPS     |
| backend   | 8000          | 8000           | HTTP      |

## Enable Banking

La redirect URL registrada en el control panel de Enable Banking debe ser:

```
https://localhost:3000/banking/callback
```

Y en el `.env` del proyecto:

```
ENABLE_BANKING_REDIRECT_URL=https://localhost:3000/banking/callback
```

## Arrancar

```bash
docker compose down
docker compose build --no-cache nginx frontend
docker compose up -d
```

## Archivos

```
nginx/
├── Dockerfile      # Imagen nginx:alpine + generación del certificado auto-firmado
├── nginx.conf      # Configuración: SSL en :3000, proxy a http://frontend:3001
└── README.md       # Este archivo
```
