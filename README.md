# DreamN

**DreamN** is a containerized fullstack web development template that uses **Docker Compose** to integrate **React**, **FastAPI**, **MariaDB**, and **Nginx**. It offers a modern, production-like environment with clear separation of frontend and backend services, streamlining development and deployment while ensuring architectural clarity and maintainability.


## Features

- ⚛️ **Frontend**: Built with React, offering a fast and modern user interface.
- 🚀 **Backend**: Powered by FastAPI, providing a robust and flexible API layer.
- 🛢️ **Database**: Uses MariaDB for reliable and high-performance data storage.
- 🔀 **Reverse Proxy**: Nginx serves as a reverse proxy, efficiently routing traffic to the appropriate services.
- 🐳 **Dockerized**: All services are containerized and orchestrated with Docker Compose, ensuring easy setup and consistent environments across development and production.


## System Requirements

| Component | Version | Description |
|-----------|---------|-------------|
| Ubuntu | 24.04.1 LTS | Operating System |
| Docker | 27.2.0 | Containerization Platform |
| Node.js | 20.18.0 | For VAPID key generation |


## How to Use

1. **Clone the repository**

   ```bash
   git clone ssh://git@172.16.0.206:2224/it/DreamN.git
   ```


2. **Move to project**

   ```bash
   cd DreamN
   ```


3. **Set up Keycloak Authentication**

   Configure your Keycloak instance and obtain the required configuration values:

   - **`KEYCLOAK_SERVER_URL`** : Your Keycloak server address

   - **`KEYCLOAK_REALM`** : Login to Keycloak Admin Console → Select your Realm name from the top-left dropdown

   - **`KEYCLOAK_CLIENT`** : In your Realm → Clients → Select the Client ID you want to use

   - **`KEYCLOAK_ADMIN_CLIENT`** : A client with administrative privileges, typically found in the Clients list with admin-related permissions. Default is usually `admin-cli`

   - **`KEYCLOAK_ADMIN_CLIENT_SECRET`** : Navigate to Admin Client → Credentials tab to find the Secret value


4. **Generate VAPID keys for Web Push notifications**

   Install web-push globally and generate VAPID keys:

   ```bash
   npm install -g web-push
   ```

   ```bash
   web-push generate-vapid-keys
   ```

   Save the generated keys for use in the next step.


5. **Configure environment variables**

   Copy `.env.example` to `.env` and edit as needed:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file and configure the following settings:

   - **Keycloak Authentication Settings**
   
      Use the values obtained from `step 3`:
      
      ```bash
      KEYCLOAK_SERVER_URL=keycloakServerURL
      KEYCLOAK_REALM=keycloakRealm
      KEYCLOAK_CLIENT=keycloakClient
      KEYCLOAK_ADMIN_CLIENT=keycloakAdminClient
      KEYCLOAK_ADMIN_CLIENT_SECRET=keycloakAdminClientSecret
      ```

   - **Web Push Settings**
   
      Replace with your generated VAPID keys from `step 4`:
      
      ```bash
      # Web push
      VAPID_PRIVATE_KEY=VAPIDPrivateKey
      VAPID_PUBLIC_KEY=VAPIDPublicKey
      VAPID_EMAIL=VAPIDPEmail
      ```

   - **Development and Production Modes**
      Set the `COMPOSE_FILE` environment variable to switch between development and production modes.


6. **Set up Nginx SSL certificates and IP whitelist**

   - Place your SSL certificates in the `nginx/ssl` directory
   - Copy `whitelist.conf.example` to `whitelist.conf` and edit as needed.

      ```bash
      cp nginx/whitelist.conf.example nginx/whitelist.conf
      ```
  
   > See [Nginx Docs](./nginx/README.md) for more details.


7. **Start the services**

   First run or after code changes:

   ```bash
   docker compose up -d --build
   ```

   Subsequent runs (no code changes):

   ```bash
   docker compose up -d
   ```


8. **Stop the services**

   ```bash
   docker compose down
   ```

## Documentation

| Directory    | Link                            |
|--------------|---------------------------------|
| Frontend     | [Docs](./frontend/README.md)    |
| Backend      | [Docs](./backend/README.md)     |
| Nginx        | [Docs](./nginx/README.md)       |


## License

This project is licensed under the [MIT License](./LICENSE).