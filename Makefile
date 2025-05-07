.PHONY:
		build up upd down restart reup reupd clean

build:
		COMPOSE_BAKE=true docker-compose build

up:
		COMPOSE_BAKE=true docker-compose up

upd:
		COMPOSE_BAKE=true docker-compose up -d

down:
		COMPOSE_BAKE=true docker-compose down

restart:
		COMPOSE_BAKE=true docker-compose stop
		COMPOSE_BAKE=true docker-compose up -d

reup:
		COMPOSE_BAKE=true docker-compose down
		COMPOSE_BAKE=true docker-compose build
		COMPOSE_BAKE=true docker-compose up

reupd:
		COMPOSE_BAKE=true docker-compose down
		COMPOSE_BAKE=true docker-compose build
		COMPOSE_BAKE=true docker-compose up -d

clean:
		COMPOSE_BAKE=true docker-compose down
		docker system prune -a
