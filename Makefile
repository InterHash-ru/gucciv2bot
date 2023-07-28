#
# Makefile (gucciv2bot)
#

NAME_BOT = gucciv2bot
RUN_BOT = app.py
SERVICE = bot.service

NAME_TRON = tron
RUN_TRON_TRACKER = usdt_tracker.py
SERVICE_TRON = tron.service

NAME_ETH = eth
RUN_ETH_TRACKER = eth_tracker.py
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
	@echo "Please use 'make <target>'"
	@echo "  run                     Run the project (python${VERSION} ${RUN_BOT})"
	@echo "  clean                   Delete cache and logs (__pycache__, errors.log)"
	@echo "  build-requirements      Save project requirements to requirements.txt"
	@echo "  install-requirements    Install requirements from requirements.txt"
	@echo "  build-systemd-bot       Generate systemd service file (data/bot.service)"
	@echo "  build-systemd-eth       Generate systemd service file (data/bot.service)"
	@echo "  build-systemd-tron      Generate systemd service file (data/bot.service)"
	@echo "  run-systemd             Start the service (${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd-bot        Stop the RUN-BOT service (${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd-eth        Stop the ETH-TRACKING service (${SYSTEMD_PATH}${SERVICE})"
	@echo "  stop-systemd-tron       Stop the TRON-TRACKING service (${SYSTEMD_PATH}${SERVICE})"

run:
	@python${VERSION} ${RUN_BOT}

clean:
	@find . -name "__pycache__" | xargs rm -rf
	@truncate -s 0 "data/logs/errors.log"
	@echo "Cache deleted successfully!"

build-requirements:
	@pipreqs --force --encoding UTF8

install-requirements:
	@pip${VERSION} install -r requirements.txt
	@echo "Successfully installed requirements from requirements.txt!"

build-systemd-bot:
	@echo "[Unit]\n\
	Description=$(NAME_BOT)\n\
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

	@echo "Systemd ${SERVICE} generated successfully!\nPath: ${SYSTEMD_PATH}${SERVICE}\n\n"

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

	@echo "Systemd ${SERVICE_ETH} generated successfully!\nPath: ${SYSTEMD_PATH}${SERVICE_ETH}\n\n"

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

	@echo "Systemd ${SERVICE_TRON} generated successfully!\nPath: ${SYSTEMD_PATH}${SERVICE_TRON}\n\n"

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
