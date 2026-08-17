FROM node:24.18-alpine3.24 AS build
WORKDIR /app
ARG VITE_PUBLIC_BASE_URL=http://localhost:5173
ENV VITE_PUBLIC_BASE_URL=${VITE_PUBLIC_BASE_URL}
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.30.4-alpine3.24
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=101:101 /app/dist /usr/share/nginx/html
RUN mkdir -p /tmp/client_body /tmp/proxy /tmp/fastcgi /tmp/uwsgi /tmp/scgi \
    && chown -R 101:101 /tmp /usr/share/nginx/html
USER 101:101
EXPOSE 8080
ENTRYPOINT []
CMD ["nginx", "-g", "daemon off;"]
