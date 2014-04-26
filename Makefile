# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.


# The package path prefix, if you want to install to another root, set DESTDIR to that root
PREFIX ?= /usr
# The command path excluding prefix
BIN ?= /bin
# The resource path excluding prefix
DATA ?= /share
# The documenation path excluding prefix and /share
DOC ?= /doc
# The command path including prefix
BINDIR ?= $(PREFIX)$(BIN)
# The resource path including prefix
DATADIR ?= $(PREFIX)$(DATA)
# The documentation path including prefix and /share
DOCDIR ?= $(DATADIR)$(DOC)
# The license base path including prefix
LICENSEDIR ?= $(DATADIR)/licenses

# Python 3 command to use in shebangs
SHEBANG ?= /usr/bin/env python3
# The name of the command as it should be installed
COMMAND ?= nightshift
# The name of the package as it should be installed
PKGNAME ?= nightshift

# Python source files
PYFILES = __main__.py interface.py

# Configuration script example files
EXAMPLES = x-window-focus


# Build rules

.PHONY: default
default: command shell

.PHONY: all
all: command shell

.PHONY: command
command: bin/nightshift

# Build rules for Python source files

bin/nightshift: obj/nightshift.zip
	mkdir -p bin
	echo '#!$(SHEBANG)' > $@
	cat $< >> $@
	chmod a+x $@

obj/nightshift.zip: $(foreach F,$(PYFILES),src/$(F))
	@mkdir -p obj
	cd src && zip ../$@ $(foreach F,$(PYFILES),$(F))

# Build rules for shell auto-completion

.PHONY: shell
shell: bash zsh fish

.PHONY: bash
bash: bin/nightshift.bash
bin/nightshift.bash: src/completion
	@mkdir -p bin
	auto-auto-complete bash --output $@ --source $<

.PHONY: zsh
zsh: bin/nightshift.zsh
bin/nightshift.zsh: src/completion
	@mkdir -p bin
	auto-auto-complete zsh --output $@ --source $<

.PHONY: fish
fish: bin/nightshift.fish
bin/nightshift.fish: src/completion
	@mkdir -p bin
	auto-auto-complete fish --output $@ --source $<


# Install rules

.PHONY: install
install: install-base install-examples install-shell

.PHONY: install
install-all: install-base install-examples install-shell

# Install base

.PHONY: install-base
install-base: install-command install-license

.PHONY: install-command
install-command: bin/nightshift
	install -dm755 -- "$(DESTDIR)$(BINDIR)"
	install -m755 $< -- "$(DESTDIR)$(BINDIR)/$(COMMAND)"

.PHONY: install-license
install-license:
	install -dm755 -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"
	install -m644 COPYING LICENSE -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"

# Install documentation

.PHONY: install-examples
install-examples: $(foreach E,$(EXAMPLES),examples/$(E))
	install -dm755 -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME)/examples"
	install -m644 $^ -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME)/examples"

# Install shell auto-completion

.PHONY: install-shell
install-shell: install-bash install-zsh install-fish

.PHONY: install-bash
install-bash: bin/nightshift.bash
	install -dm755 -- "$(DESTDIR)$(DATADIR)/bash-completion/completions"
	install -m644 $< -- "$(DESTDIR)$(DATADIR)/bash-completion/completions/$(COMMAND)"

.PHONY: install-zsh
install-zsh: bin/nightshift.zsh
	install -dm755 -- "$(DESTDIR)$(DATADIR)/zsh/site-functions"
	install -m644 $< -- "$(DESTDIR)$(DATADIR)/zsh/site-functions/_$(COMMAND)"

.PHONY: install-fish
install-fish: bin/nightshift.fish
	install -dm755 -- "$(DESTDIR)$(DATADIR)/fish/completions"
	install -m644 $< -- "$(DESTDIR)$(DATADIR)/fish/completions/$(COMMAND).fish"


# Uninstall rules

.PHONY: uninstall
uninstall:
	-rm -- "$(DESTDIR)$(BINDIR)/$(COMMAND)"
	-rm -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)/COPYING"
	-rm -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)/LICENSE"
	-rmdir -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"
	-rm -- $(foreach E,$(EXAMPLES),"$(DESTDIR)$(DOCDIR)/$(PKGNAME)/examples/$(E)")
	-rmdir -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME)/examples"
	-rmdir -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME)"
	-rm -- "$(DESTDIR)$(DATADIR)/fish/completions/$(COMMAND).fish"
	-rmdir -- "$(DESTDIR)$(DATADIR)/fish/completions"
	-rmdir -- "$(DESTDIR)$(DATADIR)/fish"
	-rm -- "$(DESTDIR)$(DATADIR)/zsh/site-functions/_$(COMMAND)"
	-rmdir -- "$(DESTDIR)$(DATADIR)/zsh/site-functions"
	-rmdir -- "$(DESTDIR)$(DATADIR)/zsh"
	-rm -- "$(DESTDIR)$(DATADIR)/bash-completion/completions/$(COMMAND)"
	-rmdir -- "$(DESTDIR)$(DATADIR)/bash-completion/completions"
	-rmdir -- "$(DESTDIR)$(DATADIR)/bash-completion"


# Clean rules

.PHONY: all
clean:
	-rm -r bin obj

