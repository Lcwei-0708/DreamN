import i18n from "@/i18n";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { useMobile } from "@/hooks/useMobile"
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/themeContext";
import { useRef, useEffect, useState } from "react";
import { useKeycloak } from "@/contexts/keycloakContext";
import { Languages, ArrowLeft, Sun, Moon, LogOut, SunMoon } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export function Dock({ className }) {
  const [dockState, setDockState] = useState("default");
  const [isInitialRender, setIsInitialRender] = useState(true);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const { theme, setTheme, themes } = useTheme();
  const { i18n: i18nInstance, t } = useTranslation();
  const { logout, authenticated } = useKeycloak();
  const isMobile = useMobile();
  const dockRef = useRef(null);

  useEffect(() => {
    setIsInitialRender(false);
  }, []);

  useEffect(() => {
    if (dockState === "default") return;
    function handleClickOutside(e) {
      if (dockRef.current && !dockRef.current.contains(e.target)) {
        setDockState("default");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dockState]);

  const themeOptions = [
    { id: themes.LIGHT, name: "Light", icon: Sun },
    { id: themes.DARK, name: "Dark", icon: Moon },
  ];

  const languageOptions = [
    { id: "en", name: "English" },
    { id: "zh-TW", name: "繁體中文" },
  ];

  const handleThemeSelect = (themeId) => {
    setTheme(themeId);
    setTimeout(() => setDockState("default"), 100);
  };

  const handleLanguageSelect = (languageId) => {
    i18n.changeLanguage(languageId);
    localStorage.setItem("app-language", languageId);
    setTimeout(() => setDockState("default"), 100);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setShowLogoutDialog(false);
    }
  };

  const contentVariants = {
    enter: {
      opacity: 0,
      x: 30,
      scale: 0.95,
      transition: {
        duration: 0.3,
        ease: [0.4, 0.0, 0.2, 1],
      },
    },
    center: {
      opacity: 1,
      x: 0,
      scale: 1,
      transition: {
        duration: 0.3,
        ease: [0.4, 0.0, 0.2, 1],
      },
    },
    exit: {
      opacity: 0,
      x: -30,
      scale: 0.95,
      transition: {
        duration: 0.3,
        ease: [0.4, 0.0, 0.2, 1],
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10, scale: 0.9 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        delay: i * 0.05,
        duration: 0.3,
        ease: [0.4, 0.0, 0.2, 1],
      },
    }),
  };

  return (
    <motion.div
      ref={dockRef}
      className={cn(
        "bg-card/80 text-card-foreground border shadow-lg rounded-xl p-2",
        "backdrop-blur-md",
        className
      )}
      layout
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 30,
        mass: 0.8,
      }}
      style={{
        minWidth: "fit-content",
      }}
    >
      {dockState === "default" && (
        <motion.div
          className="flex items-center gap-1"
          variants={contentVariants}
          initial={isInitialRender ? "center" : "enter"}
          animate="center"
          exit="exit"
          layout
        >
          <motion.div
            custom={0}
            variants={itemVariants}
            initial={isInitialRender ? "visible" : "hidden"}
            animate="visible"
          >
            <Button
              variant="ghost"
              size="sm"
              className="h-10 w-10 rounded-lg hover:bg-accent hover:text-accent-foreground transition-all duration-200"
              onClick={() => setDockState("theme")}
            >
              <SunMoon className="h-5 w-5" />
            </Button>
          </motion.div>
          <motion.div
            custom={1}
            variants={itemVariants}
            initial={isInitialRender ? "visible" : "hidden"}
            animate="visible"
          >
            <Button
              variant="ghost"
              size="sm"
              className="h-10 w-10 rounded-lg hover:bg-accent hover:text-accent-foreground transition-all duration-200"
              onClick={() => setDockState("language")}
            >
              <Languages className="h-5 w-5" />
            </Button>
          </motion.div>
          {authenticated && (
            <motion.div
              custom={2}
              variants={itemVariants}
              initial={isInitialRender ? "visible" : "hidden"}
              animate="visible"
            >
              <AlertDialog open={showLogoutDialog} onOpenChange={setShowLogoutDialog}>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-10 w-10 rounded-lg hover:bg-destructive hover:text-destructive-foreground transition-all duration-200"
                  >
                    <LogOut className="h-5 w-5" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader className={cn(
                    "flex flex-col",
                    isMobile ? "gap-2" : "gap-0"
                  )}>
                    <AlertDialogTitle>{t("logout.title")}</AlertDialogTitle>
                    <AlertDialogDescription>
                      {t("logout.message")}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter className="flex-row gap-5 sm:gap-0 mt-2">
                    <AlertDialogCancel
                      className={cn(
                        isMobile && "w-full"
                      )}
                    >
                      {t("common.cancel")}
                    </AlertDialogCancel>
                    <AlertDialogAction 
                      onClick={handleLogout}
                      className={cn(
                        "bg-destructive text-destructive-foreground hover:bg-destructive/90",
                        isMobile && "w-full"
                      )}
                    >
                      {t("common.confirm")}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </motion.div>
          )}
        </motion.div>
      )}

      {dockState === "theme" && (
        <motion.div
          className="flex items-center gap-2"
          variants={contentVariants}
          initial="enter"
          animate="center"
          exit="exit"
          layout
        >
          <motion.div
            custom={0}
            variants={itemVariants}
            initial="hidden"
            animate="visible"
          >
            <Button
              variant="ghost"
              size="sm"
              className="h-10 w-10 rounded-lg hover:bg-accent hover:text-accent-foreground transition-all duration-200"
              onClick={() => setDockState("default")}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </motion.div>
          <motion.div className="flex items-center gap-2" layout>
            {themeOptions.map((themeOption, index) => {
              const IconComponent = themeOption.icon;
              const isActive = theme === themeOption.id;
              return (
                <motion.div
                  key={themeOption.id}
                  custom={index + 1}
                  variants={itemVariants}
                  initial="hidden"
                  animate="visible"
                  layout
                >
                  <Button
                    variant={isActive ? "secondary" : "ghost"}
                    size="sm"
                    className={cn(
                      "h-10 w-10 rounded-lg flex items-center gap-1 transition-all duration-200",
                      !isActive &&
                        "hover:bg-accent hover:text-accent-foreground",
                      isActive &&
                        "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
                    )}
                    onClick={
                      isActive
                        ? undefined
                        : () => handleThemeSelect(themeOption.id)
                    }
                  >
                    <IconComponent className="h-5 w-5" />
                  </Button>
                </motion.div>
              );
            })}
          </motion.div>
        </motion.div>
      )}

      {dockState === "language" && (
        <motion.div
          className="flex items-center gap-2"
          variants={contentVariants}
          initial="enter"
          animate="center"
          exit="exit"
          layout
        >
          <motion.div
            custom={0}
            variants={itemVariants}
            initial="hidden"
            animate="visible"
          >
            <Button
              variant="ghost"
              size="sm"
              className="h-10 w-10 rounded-lg hover:bg-accent hover:text-accent-foreground transition-all duration-200"
              onClick={() => setDockState("default")}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </motion.div>
          <motion.div className="flex items-center gap-2" layout>
            {languageOptions.map((language, index) => {
              const isActive = i18nInstance.language === language.id;
              return (
                <motion.div
                  key={language.id}
                  custom={index + 1}
                  variants={itemVariants}
                  initial="hidden"
                  animate="visible"
                  layout
                >
                  <Button
                    variant={isActive ? "secondary" : "ghost"}
                    size="sm"
                    className={cn(
                      "h-10 p-3 rounded-lg flex items-center gap-1 transition-all duration-200",
                      !isActive &&
                        "hover:bg-accent hover:text-accent-foreground",
                      isActive &&
                        "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
                    )}
                    onClick={
                      isActive
                        ? undefined
                        : () => handleLanguageSelect(language.id)
                    }
                  >
                    <span className="text-xs font-medium whitespace-nowrap">
                      {language.name}
                    </span>
                  </Button>
                </motion.div>
              );
            })}
          </motion.div>
        </motion.div>
      )}
    </motion.div>
  );
}