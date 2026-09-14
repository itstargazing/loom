import { AuthBrand } from "@/components/auth-brand";
import { clerkAppearance } from "@/lib/clerk-appearance";
import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-lg px-md">
      <AuthBrand />
      <SignUp appearance={clerkAppearance} />
    </div>
  );
}
