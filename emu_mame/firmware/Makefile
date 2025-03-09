.PHONY: all clean

CC = sdcc
BUILDDIR = build

all: $(BUILDDIR)/minitel2.bin

clean:
	$(RM) -r $(BUILDDIR)

$(BUILDDIR):
	mkdir $(BUILDDIR)

$(BUILDDIR)/minitel2.ihx: minitel2.c | $(BUILDDIR)
	$(CC) -o $(BUILDDIR)/minitel2.ihx minitel2.c -mmcs51 --xram-size 0

%.bin: %.ihx
	objcopy -Iihex -Obinary $< $@
