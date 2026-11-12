COMPRESSO_CAS_VERSION = 0.1.0
COMPRESSO_CAS_SITE = $(BR2_EXTERNAL_COMPRESSO_PATH)/../src/compresso_cas
COMPRESSO_CAS_SITE_METHOD = local
COMPRESSO_CAS_LICENSE = MIT
COMPRESSO_CAS_DEPENDENCIES = python3 sqlite

define COMPRESSO_CAS_INSTALL_TARGET_CMDS
	$(INSTALL) -d $(TARGET_DIR)/usr/lib/compresso/compresso_cas
	$(INSTALL) -m 0644 $(@D)/*.py $(TARGET_DIR)/usr/lib/compresso/compresso_cas/
	$(INSTALL) -D -m 0755 $(BR2_EXTERNAL_COMPRESSO_PATH)/../scripts/compresso-cas $(TARGET_DIR)/usr/bin/compresso-cas
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_COMPRESSO_PATH)/../config/daemon-audit.conf $(TARGET_DIR)/etc/compresso/daemon-audit.conf
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_COMPRESSO_PATH)/../config/daemon-hybrid.conf $(TARGET_DIR)/etc/compresso/daemon-hybrid.conf
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_COMPRESSO_PATH)/../config/aot-rules.conf $(TARGET_DIR)/etc/compresso/aot-rules.conf
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_COMPRESSO_PATH)/../config/boot-index.conf $(TARGET_DIR)/etc/compresso/boot-index.conf
endef

$(eval $(generic-package))
