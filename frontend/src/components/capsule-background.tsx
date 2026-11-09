import type { ReactElement } from "react";

export function CapsuleBackground(): ReactElement {
  return (
    <div
      aria-hidden="true"
      className="capsule-background @container pointer-events-none absolute inset-0 -z-10 overflow-hidden"
    >
      <div className="background-capsule top-[6%] left-[4%] h-[clamp(4rem,9cqw,9rem)] w-[clamp(8rem,20cqw,20rem)] -rotate-25" />
      <div className="background-capsule top-[3%] right-[9%] hidden h-12 w-28 -rotate-30 sm:block" />
      <div className="background-capsule top-[32%] left-[18%] h-24 w-52 -rotate-25" />
      <div className="background-capsule top-[23%] right-[5%] hidden h-24 w-52 rotate-25 lg:block" />
      <div className="background-capsule right-[6%] bottom-[12%] h-[clamp(5rem,10cqw,10rem)] w-[clamp(10rem,24cqw,24rem)] -rotate-30" />
      <div className="background-capsule bottom-[5%] left-[7%] h-12 w-28 -rotate-30" />
      <div className="background-capsule top-[65%] left-[42%] hidden h-16 w-36 rotate-20 sm:block" />
    </div>
  );
}
