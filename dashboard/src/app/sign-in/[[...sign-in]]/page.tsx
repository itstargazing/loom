import { AuthBrand } from "@/components/auth-brand";
import { clerkAppearance } from "@/lib/clerk-appearance";
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-lg px-md">
      <AuthBrand />
      <SignIn appearance={clerkAppearance} />
    </div>
  );
}
