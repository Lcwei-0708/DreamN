import nginxLogo from "@/assets/nginx.svg";
import reactLogo from "@/assets/react.svg";
import fastapiLogo from "@/assets/fastapi.svg";
import mariadbLogo from "@/assets/mariadb.svg";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { userService } from '@/services/user.service';
import { useTranslation, Trans } from "react-i18next";
import { useKeycloak } from "@/contexts/keycloakContext";

function Home() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { authenticated, getToken, hasModulePermission } = useKeycloak();
  const [apiLoading, setApiLoading] = useState(false);
  const [userInfo, setUserInfo] = useState(null);

  const handleGetUserInfo = async () => {
    try {
      setApiLoading(true);
      const data = await userService.getInfo();
      setUserInfo(data);
      window.showDataToast(data, t("test.userInfo"));
    } catch (error) {
      toast.error('Failed to get user info: ' + (error?.message || error));
    } finally {
      setApiLoading(false);
    }
  };

  const handleCopyToken = async () => {
    try {
      const token = getToken();
      if (!token) {
        toast.error('Cannot get token');
        return;
      }
      await navigator.clipboard.writeText(token);
      toast.success(t("common.copied", { text: "token" }));
    } catch (error) {
      console.error('Copy token failed:', error);
      toast.error(t("common.copied_failed"));
    }
  };

  const logoClass = cn(
    "w-16 h-16",
    "sm:w-20 sm:h-20",
    "md:w-24 md:h-24",
    "lg:w-28 lg:h-28",
    "transition-all duration-300",
    "user-select-none"
  );

  return (
    <>
      <div
        className={cn(
          "min-h-screen flex flex-col items-center justify-center p-4 relative"
        )}
      >
        <h1
          className={cn(
            "text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-7 text-center",
            "text-foreground"
          )}
        >
          {t("Home.title")}
        </h1>

        <p
          className={cn(
            "mb-16 text-center text-base md:text-lg lg:text-xl max-w-2xl",
            "text-muted-foreground"
          )}
        >
          <Trans
            i18nKey="Home.description"
            components={{
              bold: <span className={cn("text-foreground font-semibold")} />,
            }}
          />
        </p>

        <div
          className={cn(
            "grid gap-8 mb-12",
            "grid-cols-2", // Mobile: 2 items per row
            "sm:grid-cols-4", // Small tablet and above: 4 items per row
            "md:gap-12", // Larger gap on tablet
            "lg:gap-16" // Even larger gap on laptop/desktop
          )}
        >
          <img
            src={nginxLogo}
            alt="Nginx"
            title="Nginx"
            className={cn(
              logoClass,
              "hover:drop-shadow-[0_8px_32px_rgba(1,150,57,0.85)]"
            )}
          />
          <img
            src={reactLogo}
            alt="React"
            title="React"
            className={cn(
              logoClass,
              "hover:drop-shadow-[0_8px_32px_rgba(97,218,251,0.95)]"
            )}
          />
          <img
            src={fastapiLogo}
            alt="FastAPI"
            title="FastAPI"
            className={cn(
              logoClass,
              "hover:drop-shadow-[0_12px_32px_rgba(0,150,136,0.85)]"
            )}
          />
          <img
            src={mariadbLogo}
            alt="MariaDB"
            title="MariaDB"
            className={cn(
              logoClass,
              "hover:drop-shadow-[0_12px_32px_rgba(221,114,0,1)]"
            )}
          />
        </div>

        {/* User Info Buttons */}
        {authenticated && (
          <div className="mb-8 flex justify-center gap-4">
            <Button
              variant="outline"
              onClick={handleGetUserInfo}
            >
              {t("test.showUserInfo")}
            </Button>
            <Button
              variant="outline"
              onClick={handleCopyToken}
              className="flex items-center gap-2"
            >
              {t("test.copyToken")}
            </Button>
          </div>
        )}

        {hasModulePermission && hasModulePermission("admin") && (
          <Button
            variant="outline"
            onClick={() => navigate("/admin")}
          >
            {t("test.admin")}
          </Button>
        )}
      </div>
    </>
  );
}

export default Home;