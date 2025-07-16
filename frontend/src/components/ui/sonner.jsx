import { Toaster as Sonner } from "sonner"
import { useTheme } from "@/contexts/themeContext"

const Toaster = ({
  ...props
}) => {
  const { theme } = useTheme()

  return (
    <Sonner
      theme={theme === 'system' ? 'system' : theme === 'dark' ? 'dark' : 'light'}
      className="toaster group"
      dir="right"
      position="top-center"
      closeButton={true}
      expand={false}
      duration={3000}
      richColors={true}
      offset={{ top: 40 }}
      maxToasts={5}
      visibleToasts={5}
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:!border-1 group-[.toaster]:shadow-lg group-[.toaster]:flex group-[.toaster]:items-center group-[.toaster]:justify-start group-[.toaster]:leading-none group-[.toaster]:py-3 dark:group-[.toaster]:bg-zinc-800 backdrop-blur-md",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          closeButton:
            "absolute -translate-y-1/3 translate-x-82 scale-120 !border-muted-foreground !bg-secondary !text-foreground hover:!bg-accent opacity-0 transition-opacity duration-200 ease-in-out pointer-events-none [.toast:hover_&]:opacity-100 [.toast:hover_&]:pointer-events-auto",
          default: "!bg-toast-normal-bg !text-toast-normal-text !border-toast-normal-border shadow-xl",
          normal: "!bg-toast-normal-bg !text-toast-normal-text !border-toast-normal-border shadow-xl",
          success: "!bg-toast-success-bg !text-toast-success-text !border-toast-success-border shadow-xl",
          warning: "!bg-toast-warning-bg !text-toast-warning-text !border-toast-warning-border shadow-xl",
          error: "!bg-toast-error-bg !text-toast-error-text !border-toast-error-border shadow-xl [&[data-type='error']]:!bg-toast-error-bg [&[data-type='error']]:!text-toast-error-text [&[data-type='error']]:!border-toast-error-border",
          info: "!bg-toast-info-bg !text-toast-info-text !border-toast-info-border shadow-xl [&[data-type='info']]:!bg-toast-info-bg [&[data-type='info']]:!text-toast-info-text [&[data-type='info']]:!border-toast-info-border",
          icon: "group-[.toast]:!mr-2 group-[.toast]:flex-shrink-0 group-[.toast]:self-center [&_svg]:!size-5 [&_.sonner-loading-bar]:!bg-toast-normal-text",
        },
      }}
      {...props} />
  );
}

export { Toaster }