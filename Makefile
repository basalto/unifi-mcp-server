SERVER     ?= 192.168.1.19
USER       ?= rjdinis
DEPLOY_DIR ?= /home/$(USER)/docker/unifi-mcp
SERVICE    ?= unifi-mcp
SSH        := ssh -o StrictHostKeyChecking=no $(USER)@$(SERVER)
SCP        := scp -o StrictHostKeyChecking=no

.PHONY: deploy install-service uninstall-service start stop restart status logs upgrade help

## deploy        Copy .env and docker-compose.yml to server
deploy:
	$(SSH) "mkdir -p $(DEPLOY_DIR)"
	$(SCP) .env docker-compose.yml $(USER)@$(SERVER):$(DEPLOY_DIR)/

## install-service  Deploy files + create and enable systemd service
install-service: deploy
	$(SSH) "printf '%s\n' \
		'[Unit]' \
		'Description=UniFi MCP Server' \
		'Requires=docker.service' \
		'After=docker.service network-online.target' \
		'Wants=network-online.target' \
		'' \
		'[Service]' \
		'Type=oneshot' \
		'RemainAfterExit=yes' \
		'WorkingDirectory=$(DEPLOY_DIR)' \
		'ExecStart=/usr/bin/docker compose up -d --pull always' \
		'ExecStop=/usr/bin/docker compose down' \
		'TimeoutStartSec=120' \
		'' \
		'[Install]' \
		'WantedBy=multi-user.target' \
		> /tmp/$(SERVICE).service \
		&& sudo mv /tmp/$(SERVICE).service /etc/systemd/system/$(SERVICE).service \
		&& sudo systemctl daemon-reload \
		&& sudo systemctl enable $(SERVICE) \
		&& sudo systemctl start $(SERVICE) \
		&& echo 'Service $(SERVICE) installed and started'"

## uninstall-service  Stop, disable and remove systemd service
uninstall-service:
	$(SSH) "sudo systemctl stop $(SERVICE) 2>/dev/null; \
		sudo systemctl disable $(SERVICE) 2>/dev/null; \
		sudo rm -f /etc/systemd/system/$(SERVICE).service; \
		sudo systemctl daemon-reload; \
		echo 'Service $(SERVICE) removed'"

## start         Start the service
start:
	$(SSH) "sudo systemctl start $(SERVICE)"

## stop          Stop the service
stop:
	$(SSH) "sudo systemctl stop $(SERVICE)"

## restart       Restart the service
restart:
	$(SSH) "sudo systemctl restart $(SERVICE)"

## status        Show service status
status:
	$(SSH) "systemctl status $(SERVICE) --no-pager -l"

## logs          Tail container logs
logs:
	$(SSH) "cd $(DEPLOY_DIR) && docker compose logs -f --tail=100"

## upgrade       Pull latest image and restart service
upgrade:
	$(SSH) "cd $(DEPLOY_DIR) && docker compose pull && sudo systemctl restart $(SERVICE)"

## help          Show available targets
help:
	@grep -E '^## ' Makefile | sed 's/^## //'
