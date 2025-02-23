.POSIX:

CONFIGFILE = config.mk
include $(CONFIGFILE)


PYFILES =\
	__main__.py\
	interface.py

EXAMPLES =\
	examples/x-window-focus


all: nightshift nightshift.bash nightshift.zsh nightshift.fish

nightshift: nightshift.zip
	printf '#!%s\n' '$(SHEBANG)' | cat - nightshift.zip > $@
	chmod -- a+x $@

nightshift.zip: $(PYFILES)
	zip $@ $(PYFILES)

nightshift.bash: completion
	auto-auto-complete bash --output $@ --source completion

nightshift.zsh: completion
	auto-auto-complete zsh --output $@ --source completion

nightshift.fish: completion
	auto-auto-complete fish --output $@ --source completion

install:
	mkdir -p -- "$(DESTDIR)$(PREFIX)/bin"
	mkdir -p -- "$(DESTDIR)$(PREFIX)/share/licenses"
	mkdir -p -- "$(DESTDIR)$(PREFIX)/share/doc/nightshift/examples"
	mkdir -p -- "$(DESTDIR)$(PREFIX)/share/bash-completion/completions"
	mkdir -p -- "$(DESTDIR)$(PREFIX)/share/zsh/site-functions"
	mkdir -p -- "$(DESTDIR)$(PREFIX)/share/fish/completions"
	test ! -d "$(DESTDIR)$(PREFIX)/share/licenses/nightshift"
	test ! -d "$(DESTDIR)$(PREFIX)/share/bash-completion/completions/nightshift"
	test ! -d "$(DESTDIR)$(PREFIX)/share/zsh/site-functions/_nightshift"
	test ! -d "$(DESTDIR)$(PREFIX)/share/fish/completions/nightshift.fish"
	cp -- nightshift "$(DESTDIR)$(PREFIX)/bin/"
	cp -- LICENSE "$(DESTDIR)$(PREFIX)/share/licenses/nightshift"
	cp -- $(EXAMPLES) "$(DESTDIR)$(PREFIX)/share/doc/nightshift/examples/"
	cp -- nightshift.bash "$(DESTDIR)$(PREFIX)/share/bash-completion/completions/nightshift"
	cp -- nightshift.zsh "$(DESTDIR)$(PREFIX)/share/zsh/site-functions/_nightshift"
	cp -- nightshift.fish "$(DESTDIR)$(PREFIX)/share/fish/completions/nightshift.fish"

uninstall:
	-rm -f -- "$(DESTDIR)$(PREFIX)/bin/nightshift"
	-rm -f -- "$(DESTDIR)$(PREFIX)/share/licenses/nightshift"
	-cd -- "$(DESTDIR)$(PREFIX)/share/doc/nightshift/" && rm -f -- $(EXAMPLES)
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/doc/nightshift/examples"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/doc/nightshift"
	-rm -f -- "$(DESTDIR)$(PREFIX)/share/fish/completions/nightshift.fish"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/fish/completions"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/fish"
	-rm -f -- "$(DESTDIR)$(PREFIX)/share/zsh/site-functions/_nightshift"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/zsh/site-functions"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/zsh"
	-rm -f -- "$(DESTDIR)$(PREFIX)/share/bash-completion/completions/nightshift"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/bash-completion/completions"
	-rmdir -- "$(DESTDIR)$(PREFIX)/share/bash-completion"

clean:
	-rm -f -- nightshift nightshift.zip nightshift.bash nightshift.fish nightshift.zsh

.PHONY: all install uninstall clean
