import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export default function Admin() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-4 items-center justify-center h-screen">
      <h1 className="text-4xl font-bold text-center">{t("test.admin")}</h1>
      <Link to="/">
        <Button>{t("common.backHome")}</Button>
      </Link>
    </div>
  );
}