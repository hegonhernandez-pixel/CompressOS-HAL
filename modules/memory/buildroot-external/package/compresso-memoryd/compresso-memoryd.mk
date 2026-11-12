COMPRESSO_MEMORYD_VERSION = 0.1.0
COMPRESSO_MEMORYD_SITE = $(BR2_EXTERNAL_COMPRESSO_PATH)/../src/compresso
COMPRESSO_MEMORYD_SITE_METHOD = local
COMPRESSO_MEMORYD_LICENSE = MIT
COMPRESSO_MEMORYD_LICENSE_FILES = ../../LICENSE

define COMPRESSO_MEMORYD_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/memoryd.py $(TARGET_DIR)/usr/libexec/compresso/memoryd.py
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_COMPRESSO_PATH)/../config/memory.conf $(TARGET_DIR)/etc/compresso/memory.conf
endef

define COMPRESSO_MEMORYD_INSTALL_INIT_SYSTEMD
	$(INSTALL) -D -m 0644 $(BR2_EXTERNAL_COMPRESSO_PATH)/../systemd/compresso-memoryd.service $(TARGET_DIR)/usr/lib/systemd/system/compresso-memoryd.service
	mkdir -p $(TARGET_DIR)/etc/systemd/system/multi-user.target.wants
	ln -sf /usr/lib/systemd/system/compresso-memoryd.service $(TARGET_DIR)/etc/systemd/system/multi-user.target.wants/compresso-memoryd.service
endef

$(eval $(generic-package))
