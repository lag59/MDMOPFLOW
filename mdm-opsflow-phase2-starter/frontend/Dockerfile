FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
ARG RAILWAY_SOURCE_CACHE_BUST=20260820_1755
RUN echo "railway-source-cache-bust=${RAILWAY_SOURCE_CACHE_BUST}" > /tmp/railway-source-cache-bust
COPY . .
RUN node -e "const fs=require('fs'); const p='app/modules/[role]/[module]/page.tsx'; const s=fs.readFileSync(p,'utf8'); if (s.includes('employee.role')) throw new Error('stale employee.role source copied into Docker build');"
RUN npm run build
ENV PORT=3000
EXPOSE 3000
CMD ["sh","-c","npm run start"]
