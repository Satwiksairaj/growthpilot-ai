FROM docker.n8n.io/n8nio/n8n:2.43.5

USER root
COPY render-entrypoint.sh /usr/local/bin/growthpilot-n8n-entrypoint
RUN chmod 0755 /usr/local/bin/growthpilot-n8n-entrypoint

USER node
ENTRYPOINT ["tini", "--", "/usr/local/bin/growthpilot-n8n-entrypoint"]
