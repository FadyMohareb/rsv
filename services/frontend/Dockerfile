# ---------- Development Stage ----------
FROM node:22 AS development

WORKDIR /app
# Install dependencies first (for caching)
COPY package*.json ./
RUN npm install
# Copy application source code
COPY . .

# For development, you can run a command such as "npm start" or "npm run dev"
CMD ["npm", "start"]
 
# ---------- Build Stage for Production ----------
FROM node:22 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# ---------- Production Stage ----------
FROM nginx:stable-alpine AS production

# Copy your custom Nginx configuration
COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf
# Copy the built assets from the build stage into Nginx's html directory
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]