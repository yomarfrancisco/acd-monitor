import * as React from "react";

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  const { className, ...rest } = props;
  return (
    <div
      className={["rounded-xl border border-white/10 bg-white/5", className]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    />
  );
}

export function CardHeader(props: React.HTMLAttributes<HTMLDivElement>) {
  const { className, ...rest } = props;
  return (
    <div
      className={["p-4 md:p-6", className].filter(Boolean).join(" ")}
      {...rest}
    />
  );
}

export function CardContent(props: React.HTMLAttributes<HTMLDivElement>) {
  const { className, ...rest } = props;
  return (
    <div
      className={["p-4 md:p-6 pt-0", className].filter(Boolean).join(" ")}
      {...rest}
    />
  );
}

export default Card;
