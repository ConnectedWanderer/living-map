FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production --no-fund --no-audit && rm -rf /root/.npm

COPY src/ ./src/

CMD ["node", "--experimental-strip-types", "src/index.ts"]
