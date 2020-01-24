# Setup findthatcharity on Dokku

## Step 1. create server

Provision server with dokku installed. Note down IP address.

## Step 2. Complete dokku setup

Visit IP address of new server in web browser and complete dokku set up

## Step 3. Install ftc-scraper app

SSH to server using root `ssh root@IP_ADDRESS` and run the following commands

```bash
# Create dokku apps
dokku apps:create ftc
dokku apps:create ftc-scrapers

# Create postgres db
sudo dokku plugin:install https://github.com/dokku/dokku-postgres.git postgres
dokku postgres:create ftc-db
dokku postgres:link ftc-db ftc
dokku postgres:link ftc-db ftc-scrapers
dokku config:set ftc DB_URI=$(dokku config:get ftc DATABASE_URL)
dokku config:set ftc-scrapers DB_URI=$(dokku config:get ftc-scrapers DATABASE_URL)

# Create elasticsearch db
sudo dokku plugin:install https://github.com/dokku/dokku-elasticsearch.git elasticsearch
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf; sudo sysctl -p
dokku elasticsearch:create ftc-es
dokku elasticsearch:link ftc-es ftc
dokku config:set ftc ES_URL=$(dokku config:get ftc ELASTICSEARCH_URL)

# Create redis to help with caching ccew scraper
sudo dokku plugin:install https://github.com/dokku/dokku-redis.git redis
dokku redis:create ftc-redis
dokku redis:link ftc-redis ftc-scrapers

# Install letsencrypt
sudo dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
dokku config:set --global DOKKU_LETSENCRYPT_EMAIL=your@email.tld
dokku letsencrypt ftc

# Add apt-get plugin
sudo dokku plugin:install https://github.com/dokku-community/dokku-apt apt

# scale the scraping process
dokku ps:scale ftc-scrapers cron=1
```

## Step 4. Add as a git remote and push

For `find-that-charity` on local machine:

```bash
git remote add dokku dokku@IP_ADDRESS:ftc
git push dokku starlette:master
```

For `find-that-charity-scrapers` on local machine:

```bash
git remote add dokku dokku@IP_ADDRESS:ftc-scrapers
git push dokku master
```

## Step 5. Run the crawlers

On the server run:

```bash
dokku enter ftc-scrapers cron sh ./crawl_all.sh
```

## Step 6. Set up the elasticsearch index

```bash
dokku run ftc python manage.py create-index
dokku run ftc python manage.py indexdata
```

## Step 7. Set up cron job so that it runs often

