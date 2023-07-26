#
# Makefile (aiogram-bot-template)
#

NAME = aiogram-bot-template
RUN_BOT = app.py
USDT_Tracker = usdt_tracker.py
ETH_Tracker = eth_traker.py
SERVICE = bot.service

#

SYSTEMD_PATH = /etc/systemd/system/
BOT_NAME = $(subst .service,, $(SERVICE))
DIR := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))

ifeq ($(OS), Windows_NT)
	VERSION = 
else
	VERSION = 3
endif

help:
	@echo "Please use 'make <target>'"
	@echo "  run                     run project (python${VERSION} ${RUN_BOT} ${USDT_Tracker} ${ETH_Tracker})"
	@echo "  clean                   Delete cache and logs (__pycache__, errors.log)"
	@echo "  build-requirements      Save requirements.txt project"
	@echo "  install-requirements    Install requirements.txt"
	@echo "  build-systemd           Generate (data/bot.service)"
	@echo "  run-systemd             Run (${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd            Stop (${SYSTEMD_PATH}${SERVICE})"
	@echo "  run-all                 Run all three files simultaneously"

run:
	@python${VERSION} ${RUN_BOT} ${USDT_Tracker} ${ETH_Tracker}

run-all:
	@python${VERSION} ${RUN_BOT} ${USDT_Tracker} ${ETH_Tracker} &

clean:
	@find . -name "__pycache__" | xargs rm -rf
	@truncate -s 0 "data/logs/errors.log"
	@echo "Cache deleted successfully!"

build-requirements:
	@pipreqs --force --encoding UTF8

install-requirements:
	@pip${VERSION} install -r requirements.txt
	@echo "Install requirements.txt successfully!"

build-systemd:
	@echo "[Unit]\n\
	Description=$(NAME)\n\
	After=syslog.target\n\
	After=network.target\n\
	\n\
	[Service]\n\
	Type=simple\n\
	User=root\n\
	WorkingDirectory=${DIR}\n\
	ExecStart=/usr/bin/python${VERSION} ${DIR}${RUN_BOT} ${USDT_Tracker} ${ETH_Tracker}\n\
	\n\
	RestartSec=10\n\
	Restart=always\n\
	\n\
	[Install]\n\
	WantedBy=multi-user.target" > ${SYSTEMD_PATH}${SERVICE}

	@echo "Systemd ${SERVICE} generated successfully!\nPath: ${SYSTEMD_PATH}${SERVICE}\n\n"

	@sudo systemctl daemon-reload
	@sudo systemctl enable ${BOT_NAME}
	@sudo systemctl start ${BOT_NAME}
	@sudo systemctl status ${BOT_NAME}

run-systemd:
	@sudo systemctl daemon-reload
	@sudo systemctl start ${BOT_NAME}
	@sudo systemctl status ${BOT_NAME}

stop-systemd:
	@sudo systemctl stop ${BOT_NAME}
	@pkill -f "python${VERSION} ${RUN_BOT}"
	@pkill -f "python${VERSION} ${USDT_Tracker}"
	@pkill -f "python${VERSION} ${ETH_Tracker}"

.PHONY = help run run-all clean build-requirements install-requirements build-systemd run-systemd stop-systemd
