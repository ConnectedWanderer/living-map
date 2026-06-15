FROM node:22-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production --no-fund --no-audit && rm -rf /root/.npm

COPY src/ ./src/

EXPOSE 3002

USER appuser
CMD ["node", "--experimental-strip-types", "src/index.ts"]