import { toast } from "sonner";
import { useEffect, useState } from "react";
import { Dock } from "@/components/Dock";
import { useTranslation } from "react-i18next";
import { useKeycloak } from "@/contexts/keycloakContext";
import { useWebSocketContext } from "@/contexts/websocketContext";
import { Toaster } from "@/components/ui/sonner";
import { DataToast } from "@/components/ui/data-toast";

export default function Layout({ children }) {
  const { addEventListener } = useWebSocketContext();
  const [dataToastOpen, setDataToastOpen] = useState(false);
  const [dataToastData, setDataToastData] = useState(null);
  const [dataToastTitle, setDataToastTitle] = useState('');

  // 全局 showDataToast 方法
  useEffect(() => {
    window.showDataToast = (data, title = 'Data') => {
      setDataToastData(data);
      setDataToastTitle(title);
      setDataToastOpen(true);
    };

    // 清理函數
    return () => {
      delete window.showDataToast;
    };
  }, []);

  // WebSocket toast
  useEffect(() => {
    if (!addEventListener) return;

    const removeSuccessListener = addEventListener("success", (message) => {
      toast.success(message.data?.message);
    });
    const removeInfoListener = addEventListener("info", (message) => {
      toast.info(message.data?.message);
    });
    const removeWarningListener = addEventListener("warning", (message) => {
      toast.warning(message.data?.message);
    });
    const removeErrorListener = addEventListener("error", (message) => {
      toast.error(message.data?.message);
    });

    return () => {
      removeSuccessListener();
      removeInfoListener();
      removeWarningListener();
      removeErrorListener();
    };
  }, [addEventListener]);

  return (
    <div>
      <Dock className="fixed top-4 right-4 z-50" />
      {children}
      <Toaster richColors={true} position="top-center" />
      <DataToast
        open={dataToastOpen}
        onClose={() => setDataToastOpen(false)}
        data={dataToastData}
        title={dataToastTitle}
        duration={5000}
      />
    </div>
  );
}
