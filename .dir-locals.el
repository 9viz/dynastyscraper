;;; Directory Local Variables
;;; For more information see (info "(emacs) Directory Variables")

((python-mode
  . ((eval . (setq-local python-shell-virtualenv-root
						 (expand-file-name (project-root (project-current)))))
	 ;; `vz/indent-dwim' logic is broken in python-mode buffers.
	 (eval . (local-unset-key (kbd "M-q"))))))
