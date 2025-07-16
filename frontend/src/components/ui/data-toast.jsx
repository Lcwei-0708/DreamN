import { toast } from "sonner";
import { useState, useEffect } from "react";
import { Copy, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";

export function DataToast({ open, data, title, onClose, duration }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const jsonStr = JSON.stringify(data, null, 2);
  duration = duration || 5000;

  useEffect(() => {
    if (open && duration > 0) {
      const timer = setTimeout(() => {
        onClose && onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [open, onClose, duration]);

  const toastVariants = {
    hidden: {
      opacity: 0,
      x: 400, // 從更遠的右邊滑入
    },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25,
        mass: 0.8,
      },
    },
    exit: {
      opacity: 0,
      x: 400, // 向右邊滑出
      transition: {
        duration: 0.3,
        ease: [0.4, 0.0, 0.2, 1],
      },
    },
  };

  return (
    <AnimatePresence mode="wait">
      {open && (
        <motion.div
          className="fixed bottom-8 right-8 z-50 max-w-lg w-full bg-popover/80 text-popover-foreground border rounded-lg shadow-xl p-4 flex flex-col gap-2 backdrop-blur-sm group"
          variants={toastVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          layout
        >
          <Button
            variant="outline"
            className="absolute -right-2 -top-2 transition-opacity duration-200 ease-in-out p-1 !size-6 rounded-full text-foreground opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto"
            onClick={onClose}
            title={t("common.close")}
            tabIndex={0}
          >
            <X className="w-4 h-4" />
          </Button>
          <motion.span 
            className="font-bold"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.3 }}
          >
            {title}
          </motion.span>
          <motion.div 
            className="relative mt-1"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.3 }}
          >
            <pre className="whitespace-pre-wrap break-all text-xs rounded-md border border-border bg-secondary text-foreground p-4 pr-10">
              {jsonStr}
            </pre>
            <Button
              variant="ghost"
              title={t("common.copy")}
              className="absolute top-1 right-1 text-foreground !size-9 p-2"
              disabled={copied}
              onClick={() => {
                navigator.clipboard.writeText(jsonStr);
                toast.success(t("common.copied", { text: title }), { position: "top-center" });
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
            >
              {copied ? (
                <Check className="w-4 h-4" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </Button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
