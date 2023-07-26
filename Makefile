#
# Makefile (gucciv2bot)
#

NAME_BOT = gucciv2bot
RUN_BOT = app.py
SERVICE = bot.service

NAME_TRON = tron
RUN_TRON_TRACKER = usdt_traker.py
SERVICE_TRON = tron.service

NAME_ETH = TRACKER-ETH-TRANSACTION
RUN_ETH_TRACKER = eth_traker.py
SERVICE_ETH = eth.service

SYSTEMD_PATH = /etc/systemd/system/
BOT_NAME = $(subst .service,, $(SERVICE))
ETH_TRACKER = $(subst .service,, $(SERVICE_ETH))
TRON_TRACKER = $(subst .service,, $(SERVICE_TRON))
DIR := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))

ifeq ($(OS), Windows_NT)
	VERSION = 
else
	VERSION = 3
endif

help:
	@echo "Пожалуйста, используйте 'make <цель>'"
	@echo "  run                     Запуск проекта (python${VERSION} ${RUN_BOT})"
	@echo "  clean                   Удалить кэш и логи (__pycache__, errors.log)"
	@echo "  build-requirements      Сохранить requirements.txt проекта"
	@echo "  install-requirements    Установить requirements.txt"
	@echo "  build-systemd-bot       Генерация файла для systemd (data/bot.service)"
	@echo "  build-systemd-eth       Генерация файла для systemd (data/bot.service)"
	@echo "  build-systemd-tron      Генерация файла для systemd (data/bot.service)"
	@echo "  run-systemd             Запуск (${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd-bot        Остановка RUN-BOT(${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd-eth        Остановка ETH-TRACKING (${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd-tron       Остановка TRON-TRACKING (${SYSTEMD_PATH}${SERVICE})"

run:
	@python${VERSION} ${RUN_BOT}

clean:
	@find . -name "__pycache__" | xargs rm -rf
	@truncate -s 0 "data/logs/errors.log"
	@echo "Кэш успешно удален!"

build-requirements:
	@pipreqs --force --encoding UTF8

install-requirements:
	@pip${VERSION} install -r requirements.txt
	@echo "Установка requirements.txt завершена успешно!"

build-systemd-bot:
	@echo "[Unit]\n\
	Description=$(NAME)\n\
	After=syslog.target\n\
	After=network.target\n\
	\n\
	[Service]\n\
	Type=simple\n\
	User=root\n\
	WorkingDirectory=${DIR}\n\
	ExecStart=/usr/bin/python${VERSION} ${DIR}${RUN_BOT}\n\
	\n\
	RestartSec=10\n\
	Restart=always\n\
	\n\
	[Install]\n\
	WantedBy=multi-user.target" > ${SYSTEMD_PATH}${SERVICE}

	@echo "Systemd ${SERVICE} успешно сгенерирован!\nПуть: ${SYSTEMD_PATH}${SERVICE}\n\n"

	@sudo systemctl daemon-reload
	@sudo systemctl enable ${BOT_NAME}
	@sudo systemctl start ${BOT_NAME}
	@sudo systemctl status ${BOT_NAME}

build-systemd-eth:
	@echo "[Unit]\n\
	Description=$(NAME_ETH)\n\
	After=syslog.target\n\
	After=network.target\n\
	\n\
	[Service]\n\
	Type=simple\n\
	User=root\n\
	WorkingDirectory=${DIR}\n\
	ExecStart=/usr/bin/python${VERSION} ${DIR}${RUN_ETH_TRACKER}\n\
	\n\
	RestartSec=10\n\
	Restart=always\n\
	\n\
	[Install]\n\
	WantedBy=multi-user.target" > ${SYSTEMD_PATH}${SERVICE_ETH}

	@echo "Systemd ${SERVICE_ETH} успешно сгенерирован!\nПуть: ${SYSTEMD_PATH}${SERVICE_ETH}\n\n"

	@sudo systemctl daemon-reload
	@sudo systemctl enable ${NAME_ETH}
	@sudo systemctl start ${NAME_ETH}
	@sudo systemctl status ${NAME_ETH}

build-systemd-tron:
	@echo "[Unit]\n\
	Description=$(NAME_TRON)\n\
	After=syslog.target\n\
	After=network.target\n\
	\n\
	[Service]\n\
	Type=simple\n\
	User=root\n\
	WorkingDirectory=${DIR}\n\
	ExecStart=/usr/bin/python${VERSION} ${DIR}${RUN_TRON_TRACKER}\n\
	\n\
	RestartSec=10\n\
	Restart=always\n\
	\n\
	[Install]\n\
	WantedBy=multi-user.target" > ${SYSTEMD_PATH}${SERVICE_TRON}

	@echo "Systemd ${SERVICE_TRON} успешно сгенерирован!\nПуть: ${SYSTEMD_PATH}${SERVICE_TRON}\n\n"

	@sudo systemctl daemon-reload
	@sudo systemctl enable ${NAME_TRON}
	@sudo systemctl start ${NAME_TRON}
	@sudo systemctl status ${NAME_TRON}


run-systemd:
	@sudo systemctl daemon-reload
	@sudo systemctl start ${BOT_NAME}
	@sudo systemctl status ${BOT_NAME}


stop-systemd-bot:
	@sudo systemctl stop ${BOT_NAME}

stop-systemd-tron:
	@sudo systemctl stop ${NAME_TRON}

stop-systemd-eth:
	@sudo systemctl stop ${NAME_ETH}

.PHONY = help run clean build-requirements install-requirements build-systemd run-systemd stop-systemd
