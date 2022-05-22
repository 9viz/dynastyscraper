;;; Directory Local Variables
;;; For more information see (info "(emacs) Directory Variables")

((python-mode
  . ((python-shell-interpreter . "./emacs-python")
	 ;; `vz/indent-dwim' logic is broken in python-mode buffers.
	 (eval . (local-unset-key (kbd "M-q"))))))
