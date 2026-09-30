const dateFmt = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  timeZone: "UTC",
});
const numFmt = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 4 });

export const fmtDate = (iso: string) => dateFmt.format(new Date(iso));
export const fmtNum = (n: number) => numFmt.format(n);
