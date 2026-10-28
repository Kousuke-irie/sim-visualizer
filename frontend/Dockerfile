FROM node:20-slim

WORKDIR /app

# lock ファイルどおりの版を入れ、CI（npm ci）と同じ依存で動かす
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
