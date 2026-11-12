COMPRESSO_ZVGA_VERSION = 0.1.0
COMPRESSO_ZVGA_SITE = $(BR2_EXTERNAL_COMPRESSO_PATH)/../../zvga
COMPRESSO_ZVGA_SITE_METHOD = local
COMPRESSO_ZVGA_LICENSE = MIT
COMPRESSO_ZVGA_DEPENDENCIES = host-cmake host-python3 host-glslang host-spirv-tools vulkan-headers vulkan-loader glslang spirv-tools
COMPRESSO_ZVGA_CONF_OPTS = \
	-DCOMPRESSO_VULKAN=ON \
	-DPython3_EXECUTABLE=$(HOST_DIR)/bin/python3 \
	-DGLSLANG_VALIDATOR:FILEPATH=$(HOST_DIR)/bin/glslangValidator \
	-DSPIRV_VAL:FILEPATH=$(HOST_DIR)/bin/spirv-val

$(eval $(cmake-package))
