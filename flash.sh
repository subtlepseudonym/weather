#!/bin/bash
firmware_path="${HOME}/download/esp32-ota-20230426-v1.20.0.bin"
if [[ "$2" != "" ]]; then
	firmware_path="$2"
fi

echo "### Erasing flash ###"
esptool.py --chip esp32 --port "$1" erase_flash
sleep 2

echo
echo "### Writing flash ###"
esptool.py --chip esp32 --port "$1" write_flash --compress 0x1000 "${firmware_path}"

