FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template

ENV API_TARGET=http://backend:8000
ENV ANALYTICS_ORIGIN=https://analytics.example.com

EXPOSE 80

CMD ["/bin/sh", "-c", \
  "envsubst '${API_TARGET} ${ANALYTICS_ORIGIN}' < /etc/nginx/templates/nginx.conf.template \
   > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
