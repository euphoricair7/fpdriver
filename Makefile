CC = gcc
CFLAGS = -Wall -Wextra -I.
LDFLAGS = -lusb-1.0

TARGET = userspace_driver
TARGET_SCAN = state_scan
SRC = src/reverse_engineer/userspace.c
SRC_SCAN = src/reverse_engineer/state_scan.c

all: $(TARGET) $(TARGET_SCAN)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(TARGET_SCAN): $(SRC_SCAN)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGET) $(TARGET_SCAN)
