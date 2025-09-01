#!/bin/bash

# HOT Travel Assistant - Podman Management Commands

case "$1" in
    "start")
        echo "🚀 Starting HOT Travel Assistant..."
        podman-compose up -d
        ;;
    "stop")
        echo "🛑 Stopping HOT Travel Assistant..."
        podman-compose stop
        ;;
    "restart")
        echo "🔄 Restarting HOT Travel Assistant..."
        podman-compose restart
        ;;
    "logs")
        if [ "$2" == "api" ]; then
            podman-compose logs -f api
        elif [ "$2" == "mysql" ]; then
            podman-compose logs -f mysql
        else
            podman-compose logs -f
        fi
        ;;
    "build")
        echo "🔨 Building containers..."
        podman-compose build
        ;;
    "clean")
        echo "🧹 Cleaning up containers and volumes..."
        podman-compose down -v
        podman system prune -f
        ;;
    "shell")
        if [ "$2" == "api" ]; then
            podman exec -it hot_travel_api /bin/bash
        elif [ "$2" == "mysql" ]; then
            podman exec -it hot_travel_mysql mysql -u root -p
        else
            echo "Usage: $0 shell [api|mysql]"
        fi
        ;;
    "status")
        echo "📊 Container Status:"
        podman ps --filter name=hot_travel
        ;;
    *)
        echo "HOT Travel Assistant - Podman Commands"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start     Start all services"
        echo "  stop      Stop all services"
        echo "  restart   Restart all services"
        echo "  logs      Show logs (add 'api' or 'mysql' for specific service)"
        echo "  build     Build containers"
        echo "  clean     Clean up containers and volumes"
        echo "  shell     Access container shell [api|mysql]"
        echo "  status    Show container status"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs api"
        echo "  $0 shell mysql"
        ;;
esac